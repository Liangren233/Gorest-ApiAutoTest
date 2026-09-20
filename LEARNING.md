# Gorest-ApiAutoTest 项目学习文档(小白版)

> 本文档面向刚接触本项目的同学,目标:看完后能说清「项目结构 / 一次测试如何跑起来 / 变量在哪些函数间流转 / 每个机制为什么这样设计」。

---

## 一、这个项目是什么

一个**接口自动化测试框架**,测的是 GoREST 公开 API(`https://gorest.co.in/public/v2`)。
- 测什么:users / posts / comments / todos 四大资源模块的 CRUD(增删改查)+ 负向边界场景
- 怎么测:把用例写在 YAML 里(数据驱动),pytest 读 YAML 自动跑,Allure 出报告,Jenkins 定时触发,企微推送结果
- 规模:42 条用例(24 条 happy path + 18 条负向)

一句话:**你只改 YAML 就能加用例,不改 Python 代码**。

---

## 二、目录结构(每个文件干什么)

```text
Gorest-ApiAutoTest/
├── pytest.ini                # ① pytest 配置:pythonpath、中文用例名不转义、默认出 Allure 结果
├── Jenkinsfile               # ② Jenkins 流水线:轮询+定时触发,跑测试+出报告
├── requirements.txt          # ③ Python 依赖清单
├── .env / .env.example       # ④ 凭据:GOREST_TOKEN(真实/模板)
│
├── config/
│   └── env.yaml              # ⑤ 多环境配置:test/prod 的 base_url + token 变量名
│
├── core/                     # ===== 核心层(通用能力,不含 pytest 协议)=====
│   ├── client.py             # ⑥ ApiClient:环境配置加载 + HTTP 封装 + Bearer 鉴权 + auth 开关
│   ├── context.py            # ⑦ 用例数据流转:load_yaml 加载 / resolve 变量替换 / extract 提取
│   ├── assertor.py           # ⑧ Assertor:三档断言(status/contains/schema)
│   └── notifier.py           # ⑨ 企微通知:消息组装+发送(纯函数,不依赖 pytest)
│
├── data/
│   └── users.yaml            # ⑩ 用例数据:42 条用例全在这里(数据驱动核心)
│
├── tests/
│   ├── conftest.py           # ⑪ pytest 粘合层:fixture + 参数化 + 薄钩子(业务委托 core/)
│   └── test_users.py         # ⑫ 测试主体:只剩 test_api 一个函数(编排,不写框架细节)
│
└── report/tmp/               # ⑬ Allure 原始结果(每次自动清空重建)
```

**三层分工**(重点理解):
| 层 | 目录 | 职责 | 改动频率 |
|---|---|---|---|
| 数据层 | `data/` | 存用例 | 经常改(加用例) |
| 核心层 | `core/` | HTTP/断言/数据流转/通知等可复用能力 | 很少改 |
| 测试层 | `tests/` | pytest 粘合层(fixture/钩子)+ 测试函数编排 | 偶尔改 |

---

## 三、一次 pytest 运行的完整链路

你在终端敲 `pytest` 回车后,发生了这些事(按时间顺序):

```text
1. pytest 启动,读 pytest.ini
   └─ addopts: -s -v --alluredir=report/tmp --clean-alluredir
      (打印+详细+结果写 report/tmp+先清空)

2. pytest 收集阶段(还没跑用例)
   ├─ 读 tests/conftest.py,发现 pytest_generate_tests 钩子  ← 关键!
   ├─ 钩子调用 core.context.load_yaml("data/users.yaml") 读到 42 条 case
   ├─ 对每条 case 调 metafunc.parametrize("case", cases, ids=[用例名])
   └─ 结果:生成 42 条 test_api[用例名] 测试 ID
   (此时用例还没执行,只是"登记"了 42 条要跑)

3. session 开始
   ├─ 触发 pytest_sessionstart 钩子(conftest.py)
   └─ 记录开始时间 _session_start_time,统计清零

4. 逐条执行 42 条用例(每条都走 test_api 函数)
   对每条用例:
   ├─ 注入 client fixture(每次新建 ApiClient)
   ├─ 注入 vars_pool fixture(session 级,整个 session 共享一个)
   ├─ test_api(case, client, vars_pool) 执行(只做编排,能力在 core/):
   │   ├─ context.resolve:把 url/json/params 里的 ${var} 替换成 vars_pool 的值
   │   ├─ client.request(...):发 HTTP 请求(默认带 token)
   │   ├─ context.extract:从响应按 JSONPath 提取字段写入 vars_pool
   │   ├─ 注册 cleanup(若 case 有 cleanup 字段且提取到 id)
   │   └─ Assertor(resp).run(expects):三档断言
   └─ Allure 记录每个 step

5. session 结束
   ├─ vars_pool fixture teardown:遍历 __cleanup__ 兜底 DELETE 资源
   ├─ pytest_sessionfinish 钩子:统计 passed/failed/skipped
   └─ 委托 core.notifier.notify:若配了 WECHAT_WEBHOOK,发企微通知
```

---

## 四、核心机制图解

### 4.1 数据驱动:YAML → 参数化用例

**目标**:YAML 里每条 case 变成一条独立测试。

**用例数据结构**(每条 case 的字段):
```yaml
- name: "创建新用户"          # 用例名,作测试 ID 和报告标题
  request:                    # 请求描述
    method: POST
    url: "/users"
    json: {name, email, gender, status}  # 请求体(可选)
    params: {page: 1}         # query 参数(可选)
    auth: false               # 是否带 token,默认 true(可选)
  expects:                    # 期望
    status: 201               # HTTP 状态码(必填)
    contains: {field: value}  # 字段精确匹配(可选)
    schema:                 # JSON Schema 结构契约(可选,基于 jsonschema 库)
      type: object
      required: [id, name]
      properties:
        id: {type: integer}
        name: {type: string}
  extract:                    # 提取响应字段到变量池(可选)
    created_user_id: $.id
  cleanup:                    # 声明要清理的资源(可选)
    - "users:${created_user_id}"
```

**实现**:在 [tests/conftest.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/tests/conftest.py) 的 `pytest_generate_tests` 钩子:
```python
def pytest_generate_tests(metafunc):
    if "case" in metafunc.fixturenames:
        raw = load_yaml("data/users.yaml")   # load_yaml 来自 core.context
        cases = raw["cases"]
        ids = [c.get("name", "未命名") for c in cases]
        metafunc.parametrize("case", cases, ids=ids)
```

- `pytest_generate_tests` 是 pytest 收集阶段钩子,**运行时**动态读 YAML
- `metafunc.parametrize("case", cases, ...)` 把 42 条 case 作为参数 `case` 注入
- `ids` 用用例名,所以测试 ID 显示成 `test_api[创建新用户]` 而不是 `test_api[0]`

### 4.2 变量池 vars_pool:session 级共享

**是什么**:一个 dict,整个 session(一次 pytest 运行)所有用例共享同一个。

**初始化**([tests/conftest.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/tests/conftest.py) 的 `vars_pool` fixture):
```python
@pytest.fixture(scope="session")
def vars_pool():
    pool = {
        "timestamp": int(time.time() * 1000),     # 毫秒级时间戳,用于生成唯一 email
        "due_date": (now+7天).isoformat(),         # 未来7天,用于 todos 的 due_on
        "__cleanup__": [],                         # 待清理资源列表
    }
    yield pool        # ← 用例执行阶段,vars_pool 就是这个 pool
    # teardown(下面 4.7 讲)
```

**为什么 session 级**:CRUD 是跨用例链路——"创建用户"提取的 id 要给"更新/删除"用,function 级每次新建就断了关联。

**生命周期**:
```text
session 开始 → pool 初始化(timestamp/due_date/__cleanup__)
        ↓
  42 条用例共用这个 pool,每条用例的 extract 往里写新变量
        ↓
session 结束 → yield 之后的 teardown 跑 cleanup
```

### 4.3 变量替换 ${var}

**在哪做**:test_api 发请求**之前**,调用 [core/context.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/core/context.py) 的 `resolve`。

```python
def resolve(text, vars_pool):
    for k, v in vars_pool.items():
        text = text.replace(f"${{{k}}}", str(v))   # ${user_id} → 实际 id
    return text
```

**例子**:
- vars_pool 里有 `user_id=123`
- case 的 url 是 `/users/${user_id}`
- `resolve` 把它变成 `/users/123` 再发请求

`resolve_obj` 是递归版,处理 dict/list 里的嵌套字符串(如 json body 里的 `${timestamp}`)。

**为什么在 core 层而不在 client 层**:client 是通用 HTTP 工具,不该知道测试变量语义;且替换需要 vars_pool 上下文,client 无状态。变量替换属于"用例数据运行时处理",故与 load_yaml/extract 同居 context.py。**关注点分离**。

### 4.4 JSONPath 提取 extract

**作用**:从响应 JSON 按 JSONPath 表达式取字段,写入 vars_pool。实现在 [core/context.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/core/context.py) 的 `extract`。

**两种表达式**:
| 表达式 | 响应结构 | 取什么 |
|---|---|---|
| `$.id` | `{"id":1,...}`(dict) | 根对象 id |
| `$[0].id` | `[{"id":1},...]`(list) | 数组首元素 id |

**流程**:
```text
resp.json() → jsonpath.jsonpath(data, expr) → val 写入 vars_pool[var_name]
```

**例子**:用例"查询用户列表"响应是 `[{"id":123,...}, {...}]`,extract 配 `user_id: "$[0].id"`,提取后 `vars_pool["user_id"]=123`,后续用例 url 用 `/users/${user_id}` 就能引用。

**提取失败怎么办**:jsonpath 无匹配时打印 `[WARN]` 但**不中断**,vars_pool 里该变量保持不存在。后续 `${var}` 替换时找不到就原样保留,通常导致 404。这是之前踩过的坑(见 FAQ)。

### 4.5 三档断言引擎 Assertor

**三档由弱到强**([core/assertor.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/core/assertor.py)):

| 档位 | 方法 | 校验什么 | 失败信息 |
|---|---|---|---|
| status | `assert_status` | HTTP 状态码 | 期望 200,实际 404 |
| contains | `assert_contains` | 字段值精确匹配 | 字段值不符 |
| schema | `assert_schema` | JSON Schema 结构契约 | type/required/properties/items/enum 等不符 |

**contains 的 list 分支**(重点):GoREST 的 422 错误返回的是**数组**:
```json
[{"field":"email","message":"has already been taken"}]
```
所以 `assert_contains` 检测到响应是 list 时,用 `any(...)` 遍历找是否存在元素含 `field=email`([core/assertor.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/core/assertor.py))。dict 响应则直接比对字段值。

**run 方法**([core/assertor.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/core/assertor.py))按顺序跑三档:
```python
def run(self, expects):
    self.assert_status(expects.get("status", 200))   # 1. 先断状态码
    if "contains" in expects: self.assert_contains(...)  # 2. 再断字段值
    if "schema" in expects:   self.assert_schema(...)   # 3. 最后断结构
```
任一档失败抛 AssertionError,pytest 标记该用例 failed。

### 4.6 鉴权控制 auth

**默认行为**:client.request 自动从环境变量读 `GOREST_TOKEN`,注入 `Authorization: Bearer <token>` 头([core/client.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/core/client.py))。

**auth=false 覆盖**:case 的 request 里写 `auth: false`,test_api 透传给 client.request,跳过 token 注入 → 触发 401 鉴权失败场景。

```text
case.request.auth(默认True) → test_api 读取 → client.request(auth=...) → 是否注入 token
```

**为什么这样设计**:默认行为不变(向后兼容),只在需要 401 场景时关闭,最小侵入。

### 4.7 数据兜底清理 cleanup

**痛点**:用例中途失败导致 DELETE 步骤没执行,创建的资源残留在 GoREST,下次运行 email 碰撞 422。

**机制**:
1. case 有 `cleanup: ["users:${created_user_id}"]` 字段
2. test_api 在 extract 之后,把 `"users:123"` append 到 `vars_pool["__cleanup__"]`
3. session 结束,vars_pool fixture 的 yield 之后 teardown 执行([tests/conftest.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/tests/conftest.py)):
```python
yield pool
# ↓ session 结束到这里
if pool["__cleanup__"]:
    cleaner = ApiClient()
    for resource, rid in reversed(pool["__cleanup__"]):
        resp = cleaner.request("DELETE", f"/{resource}/{rid}")
        # 404 是预期(正常用例已自删),其他码才告警
```

**关键点**:
- cleanup 注册的时机:extract 提取到 id **且** case 有 cleanup 字段,才 append
- 如果创建用例本身失败(422),没 id 提取,不会注册 → 不会泄漏
- 正常流程用例自删了,teardown 再删返回 404 是预期(无害冗余)

### 4.8 企微通知

**职责拆分**:
- [tests/conftest.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/tests/conftest.py) 只保留 pytest 薄钩子:`pytest_sessionfinish` 把统计结果委托出去
- [core/notifier.py](file:///c:/Users/zdd20/PycharmProjects/PythonProject1/Gorest-ApiAutoTest/core/notifier.py) 承担业务:`build_message` 组装 markdown + `send_wechat` 发送 + `notify` 门面(未配 webhook 静默跳过)

**数据来源**:
- passed/failed/skipped:由 `pytest_runtest_makereport` 钩子每条用例结束后累加到 `_test_stats`
- JOB_NAME/BUILD_NUMBER:Jenkins 注入的环境变量(本地有默认值)
- 耗时:`_session_start_time` 到现在的差值

**通知内容**:markdown 格式,含项目名/构建号/开始时间/耗时/通过-失败-跳过统计。失败 `@all`,成功静默。没配 `WECHAT_WEBHOOK` 则跳过。

**为什么业务逻辑放 core/**:通知与 pytest 协议无关,纯函数便于单测,未来加钉钉/邮件渠道只改 notifier.py,conftest 不动。

---

## 五、函数调用关系总图

```text
pytest 启动
│
├─ pytest_generate_tests(metafunc)              [tests/conftest.py]
│   └─ load_yaml("data/users.yaml")            [core/context.py]
│       └─ metafunc.parametrize("case", cases)  → 生成 42 条用例 ID
│
├─ pytest_sessionstart(session)                [tests/conftest.py] → 记录开始时间
│
└─ 对每条 case 执行 test_api(client, case, vars_pool)  [tests/test_users.py](只编排)
    │
    ├─ resolve_obj(req["json"], vars_pool)      [core/context.py] → 替换 ${var}
    ├─ client.request(method, url, auth, ...)   [core/client.py]
    │   └─ requests.request(...)                → 真实 HTTP
    │
    ├─ extract(resp, extract_cfg, vars_pool)    [core/context.py] → JSONPath 提取写回 vars_pool
    │   (若 case.cleanup 且提取到 id → append __cleanup__)
    │
    └─ Assertor(resp, name).run(expects)        [core/assertor.py]
        ├─ assert_status
        ├─ assert_contains
        └─ assert_schema

session 结束
│
├─ vars_pool teardown                           [tests/conftest.py] → 兜底 DELETE __cleanup__
└─ pytest_sessionfinish                         [tests/conftest.py]
    └─ notifier.notify(...)                     [core/notifier.py] → 企微通知
```

---

## 六、一条用例的完整生命周期(以"创建新用户"为例)

case 数据:
```yaml
- name: "创建新用户"
  request: {method: POST, url: "/users", json: {name: "AutoTest User ${timestamp}", email: "autotest_${timestamp}@example.com", gender: "male", status: "active"}}
  expects: {status: 201}
  extract: {created_user_id: $.id}
  cleanup: ["users:${created_user_id}"]
```

执行步骤:
```text
1. pytest 注入 vars_pool(session 级,此时已有 timestamp=1789718766889)
2. test_api 拿到 case
3. resolve_obj(req["json"], vars_pool):
   json = {name: "AutoTest User 1789718766889", email: "autotest_1789718766889@example.com", ...}
4. url = resolve("/users", vars_pool) = "/users"(无变量)
5. client.request("POST", "/users", auth=True, json=...):
   ├─ 拼 full_url = "https://gorest.co.in/public/v2/users"
   ├─ 注入 headers["Authorization"] = "Bearer 67a99a..."
   └─ requests.request("POST", full_url, headers=..., json=...) → resp
   resp.status_code = 201, resp.json() = {"id":8627078, "name":..., "email":...}
6. extract(resp, extract_cfg, vars_pool):
   extract_cfg = {created_user_id: "$.id"}
   jsonpath 匹配 → val = resp.json()["id"] = 8627078
   vars_pool["created_user_id"] = 8627078
7. 注册 cleanup:
   case 有 cleanup: ["users:${created_user_id}"]
   resolve 后 = "users:8627078"
   vars_pool["__cleanup__"].append(("users", 8627078))
8. Assertor(resp, "创建新用户").run({status: 201}):
   assert resp.status_code == 201 → 通过
9. Allure 记录 5 个 step 的附件
```

---

## 七、vars_pool 数据流转(如何从空到满)

```text
session 开始:
  vars_pool = {timestamp: 1789718766889, due_date: "2026-09-25T...", __cleanup__: []}

用例1 [查询用户列表]:
  extract user_id: "$[0].id" → resp=[{"id":123,...}]
  vars_pool += {user_id: 123}

用例2 [查询指定用户详情]:
  url: "/users/${user_id}" → resolve → "/users/123"
  (无 extract)

用例3 [创建新用户]:
  json.email: "autotest_${timestamp}@" → 替换 timestamp
  extract created_user_id: "$.id" → resp={"id":456,...}
  vars_pool += {created_user_id: 456}
  cleanup 注册: __cleanup__ += [("users", 456)]

用例4 [更新刚创建的用户]:
  url: "/users/${created_user_id}" → "/users/456"

用例5 [删除刚创建的用户]:
  url: "/users/${created_user_id}" → "/users/456"
  DELETE 成功 204

用例6 [验证用户已被删除]:
  url: "/users/${created_user_id}" → 404(预期)
  (注意:created_user_id 仍在 vars_pool,但资源已删)

...

session 结束 teardown:
  __cleanup__ = [("users", 456), ...]
  循环 DELETE /users/456 → 404(已删,无害)
```

**要点**:vars_pool 是**只增不减**的累积,前序用例写入的变量后序用例都能读。这就是"跨用例变量关联"的本质。

---

## 八、关键代码逐段解析

### 8.1 client.py(为什么有 auth 参数)

```python
# [core/client.py#L18-L31]
class ApiClient:
    def request(self, method, url, auth=True, **kwargs):
        headers = kwargs.get("headers", {})
        if auth:                                    # ← 默认带 token
            token = os.getenv(TOKEN_ENV_KEY)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        full_url = url if url.startswith("http") else f"{BASE_URL}{url}"
        resp = requests.request(method, full_url, **kwargs)
        self.last_resp = resp
        return resp                                 # ← 只调一次!不要写两次!
```

注意:`return resp` 只发一次请求。早期 bug 是末尾又 `return requests.request(...)` 导致非幂等操作(POST 创建)执行两次。

### 8.2 assertor.py(三档断言 + list 分支)

```python
# contains 对 dict 和 list 响应的不同处理
def assert_contains(self, expects: dict):
    actual = self.resp.json()
    for k, v in expects.items():
        if isinstance(actual, list):                # 422 错误数组
            found = any(isinstance(item, dict) and item.get(k) == v for item in actual)
            assert found, "..."
        else:                                       # dict 响应
            assert k in actual
            assert actual[k] == v
```

### 8.3 conftest.py(fixture teardown 兜底)

```python
# vars_pool 的 yield 后 teardown
yield pool                      # ← 用例执行阶段返回 pool
# session 结束:
if pool["__cleanup__"]:
    cleaner = ApiClient()
    for resource, rid in reversed(pool["__cleanup__"]):
        resp = cleaner.request("DELETE", f"/{resource}/{rid}")
```

`reversed` 是后注册的先删(通常是最新的依赖)。

---

## 九、常见疑问 FAQ

**Q1: 为什么 timestamp 用毫秒级?**
A: 秒级时同秒内多次运行会生成相同 email,撞上上次残留用户导致 422 邮箱占用。毫秒级碰撞概率极低。

**Q2: 为什么有的负向用例只断 status 不断字段?**
A: 早期写的负向用例,那时 assert_contains 还不支持 list 响应。后来增强了,新写的都加 contains。旧的没全补。

**Q3: cleanup 返回 404 是失败吗?**
A: 不是。404 说明资源已不存在(可能 happy path 已自删),目的已达。只有非 404 的错误码才告警。

**Q4: vars_pool 是线程安全的吗?能并行吗?**
A: 不能。session 级 vars_pool 是共享状态,pytest-xdist 并行时多 worker 会竞争。要并行需改成 worker 级或用 --dist=loadgroup。

**Q5: 如果创建用例失败了(422),cleanup 会注册吗?**
A: 不会。注册前提是 extract 提取到 id,创建失败响应没 id,extract 拿 None 不写入,也不注册 cleanup。所以不会泄漏。

**Q6: ${var} 替换在哪一层做?**
A: 测试编排层(test_api)调用 core.context.resolve,在发请求之前完成。client 层不感知测试变量,保持通用;替换/提取/加载等同属"用例数据运行时处理"的函数集中在 core/context.py,供所有 test_*.py 复用。

**Q7: 为什么用 YAML 不用 Excel?**
A: YAML 支持注释/嵌套/git diff 友好;Excel 嵌套结构表达难且二进制 diff 不好。接口测试 json body 是嵌套的,YAML 最合适。

**Q8: 如何加一条新用例?**
A: 在 `data/users.yaml` 的 cases 列表追加一段(name/request/expects),保存。无需改任何 Python。

---

## 十、动手练习(验证你理解了)

1. 在 `data/users.yaml` 末尾加一条:GET `/users` 只断 status 200,跑 pytest 看是否多一条用例。
2. 给某条用例加 `extract: {test_var: "$[0].id"}`,在下一条用例的 url 里用 `${test_var}`,观察 vars_pool 附件。
3. 故意把某条用例的 `expects.status` 改成错误值,看 Allure 报告里失败信息和响应体附件。
4. 把一条用例的 `auth` 设为 false,观察 401 响应。
5. 给一条创建用例加 `cleanup: ["users:${created_user_id}"]`,看 session 结束日志里的 `[CLEANUP]` 输出。

完成这 5 个练习,你就真正理解这个框架了。
