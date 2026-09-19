# Gorest 接口自动化测试框架

基于 pytest + YAML 数据驱动的接口自动化测试框架,覆盖 GoREST API 四大资源模块(users/posts/comments/todos)的 CRUD 与负向场景,集成 Bearer 鉴权、Allure 分层报告、Jenkins CI 流水线与企微通知。

> **[LEARNING.md](LEARNING.md)** —— 面向小白的学习文档,详解项目结构、变量流转、函数调用链路与 8 大核心机制

## 项目特性

- **数据驱动**:用例与代码解耦,所有用例写在 YAML,新增用例零代码改动
- **跨用例变量关联**:session 级变量池支持 `${var}` 语法,前序用例提取的 ID 可在后序用例引用
- **三档断言引擎**:status(状态码)/ contains(字段精确匹配,支持 dict 与 list 响应)/ schema(字段存在性+类型)
- **JSONPath 提取**:基于 jsonpath 库,支持 `$.id` / `$[0].id` / 嵌套路径
- **鉴权可覆盖**:`auth: false` 跳过 token 注入,支持 401 鉴权失败场景
- **数据兜底清理**:session 级 cleanup fixture,用例中途失败也自动清理垃圾数据
- **42 条用例**:24 条 happy path CRUD + 18 条负向(401/404/422 全覆盖)
- **CI 闭环**:Jenkins 轮询+定时触发,Allure 报告归档,企微结果通知

## 技术栈

| 组件 | 用途 |
|---|---|
| Python 3.12 | 测试运行环境 |
| pytest 9.x | 测试引擎 + 参数化驱动 |
| requests | HTTP 客户端 |
| PyYAML | 用例数据管理(数据/代码分离) |
| jsonpath | JSON 响应字段提取($.id / $[0].id / 嵌套路径) |
| python-dotenv | 本地 .env 凭据加载 |
| Allure | 可视化测试报告 |
| GoREST API | 测试目标(Bearer Token 鉴权) |
| Jenkins | CI/CD 流水线 |
| 企微 Webhook | 构建结果实时通知 |

## 快速开始

> 完整的本地配置清单与校验步骤见 [SETUP.md](SETUP.md)。以下为精简版。

### 1. 环境要求

| 项 | 版本 | 是否必须 |
|---|---|---|
| Python | 3.12+ | 必须 |
| Git | 任意 | 必须 |
| Allure CLI | 2.x | 可选(本地查看报告用) |

### 2. 克隆仓库

```bash
#gitee 仓库(国内优先)
git clone https://gitee.com/liangren2334/api-auto-test.git
cd Gorest-ApiAutoTest-test

#github 仓库
git clone https://github.com/liangren233/api-auto-test.git
cd Gorest-ApiAutoTest-test
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制模板并填入自己的 GoREST Token(从 https://gorest.co.in/api-register 申请):

```bash
cp .env.example .env
# 编辑 .env,填入 GOREST_TOKEN
```

`.env` 已被 `.gitignore` 忽略,不会提交。环境变量说明:

| 环境变量 | 必填 | 用途 |
|---|---|---|
| `GOREST_TOKEN` | 是 | GoREST API Bearer Token |
| `WECHAT_WEBHOOK` | 否 | 企微通知 Webhook,不配则跳过;CI 由 Jenkins 凭据 `wechat-webhook` 注入 |
| `RUN_ENV` | 否 | 运行环境,默认 `test`,可选 `prod`(对应 `config/env.yaml` 的 base_url) |

`ApiClient` 启动时通过 `python-dotenv` 自动加载 `.env`,`GOREST_TOKEN` 注入到每个请求的 `Authorization: Bearer <token>` 头。

### 5. 运行测试

```bash
pytest
```

期望输出:`42 passed`,末尾打印 `[NOTIFY] Wechat sent successfully`(配了 Webhook 时)。

### 6. 查看报告(可选)

```bash
allure serve report/tmp
```

浏览器自动打开分层报告,每个用例含请求信息、变量池快照、断言、响应体附件。

## 目录结构

```text
Gorest-ApiAutoTest/
├── Jenkinsfile               # Jenkins Pipeline:Checkout → Setup → Run Tests → Allure,内置 triggers(pollSCM/cron)
├── pytest.ini                # pytest 配置(pythonpath + 中文 ID 修复 + Allure 结果输出)
├── requirements.txt          # Python 依赖清单
├── README.md                 # 项目说明(本文档)
├── LEARNING.md               # 小白学习文档:项目结构/变量流转/函数调用链路(新手必读)
├── SETUP.md                  # 本地配置需求文档(clone 后必读,含校验清单 + FAQ)
├── LICENSE                   # 开源许可证
├── .env / .env.example       # 凭据:.env 真实(被 gitignore)/ .env.example 模板(入库)
├── .gitignore                # Git 忽略规则
├── config/
│   └── env.yaml              # 多环境 base_url + token 变量名(test/prod)
├── core/                     # 核心层:可复用能力,不依赖 pytest 协议
│   ├── client.py             # ApiClient:环境加载 + HTTP 封装 + Bearer 鉴权 + auth 开关
│   ├── context.py            # 用例数据流转:load_yaml 加载 / ${var} 替换 / JSONPath 提取
│   ├── assertor.py           # 断言引擎:status / contains / schema 三档校验
│   └── notifier.py           # 企微通知:消息组装 + 发送(纯函数)
├── data/
│   └── users.yaml            # 用例数据:42 条(24 happy + 18 负向)
├── report/
│   └── tmp/                  # Allure 原始结果(自动清空重建,被 gitignore)
└── tests/                    # 测试层:pytest 粘合 + 用例编排
    ├── conftest.py           # fixture + 参数化 + cleanup 兜底 + 薄钩子(业务委托 core/)
    └── test_users.py         # 单一 test_api:替换 → 请求 → 提取 → 清理注册 → 断言
```

## 核心设计

### 1. 数据驱动

用例完全写在 YAML,与测试代码解耦。通过 `pytest_generate_tests` 自动加载 `data/users.yaml` 实现参数化:

```yaml
- name: "查询用户列表"
  request:
    method: GET
    url: "/users"
    params:
      page: 1
      per_page: 2
  expects:
    status: 200
  extract:
    user_id: "$[0].id"
```

新增用例只需在 YAML 追加,无需改 Python 代码。

### 2. 跨用例变量关联

session 级 `vars_pool` 变量池,支持 `${var}` 语法跨用例传递数据:

```yaml
# 用例 A 提取
- name: "创建新用户"
  ...
  extract:
    created_user_id: $.id
    created_user_email: $.email

# 用例 B 引用
- name: "更新刚创建的用户"
  request:
    method: PATCH
    url: "/users/${created_user_id}"
```

变量池初始含 `timestamp`(毫秒级,用于生成唯一邮箱)和 `due_date`(未来7天 ISO,用于待办),运行时由各用例 extract 累积。

### 3. 断言引擎

三档断言,适配 dict 与 list 两种响应结构:

| 档位 | 用途 | 示例 |
|---|---|---|
| `status` | HTTP 状态码精确匹配 | `status: 200` |
| `contains` | 响应字段精确匹配 | `contains: {message: "Resource not found"}` |
| `schema` | 字段存在性 + 类型校验 | `schema: {id: {type: int}}` |

`contains` 同时支持:
- **dict 响应**:直接校验字段值(如 404 `{"message":"Resource not found"}`)
- **list 响应**:校验是否存在元素含指定 field=value(如 422 错误数组 `[{"field":"email","message":"..."}]`)

负向用例示例(422 错误数组断言具体错误字段):
```yaml
- name: "负向-用已占用邮箱创建用户"
  ...
  expects:
    status: 422
    contains:
      field: "email"
      message: "has already been taken"
```

### 4. 鉴权控制(auth)

默认所有请求自动注入 Bearer Token。用例可通过 `auth: false` 跳过注入,覆盖 401 鉴权失败场景:

```yaml
- name: "负向-无token创建用户"
  request:
    method: POST
    url: "/users"
    auth: false
    json:
      name: "No Auth User"
      email: "noauth_${timestamp}@example.com"
      gender: "male"
      status: "active"
  expects:
    status: 401
    contains:
      message: "Authentication failed"
```

### 5. 数据兜底清理(cleanup)

用例可在 `cleanup` 字段声明创建的资源,session 结束时由 `vars_pool` fixture teardown 兜底删除,避免用例中途失败残留垃圾数据:

```yaml
- name: "创建新用户"
  ...
  extract:
    created_user_id: $.id
  cleanup:
    - "users:${created_user_id}"
```

正常流程下用例自创建自删除,cleanup 不触发;若中途断言失败导致删除步骤未执行,session teardown 会兜底删除已注册资源,根治跨运行数据残留导致的冲突。

### 6. JSONPath 提取

基于 `jsonpath` 库,支持标准 JSONPath 表达式:

| 表达式 | 含义 | 适用响应 |
|---|---|---|
| `$.id` | 根对象的 id 字段 | dict(创建返回单对象) |
| `$[0].id` | 数组首元素的 id | list(查询返回数组) |
| `$.data[0].user_id` | 嵌套路径 | 复杂嵌套响应 |

### 7. 密钥管理

Token 通过环境变量管理,代码不硬编码:
- **本地**:`.env` 文件(已加 `.gitignore`),由 `python-dotenv` 自动加载
- **CI**:Jenkins Credentials 注入同名环境变量

### 8. Allure 报告

每个用例自动生成分层步骤:
- 发送请求(含 method / url / body / params)
- 提取变量(含变量池 JSON 快照)
- 注册清理资源
- 执行断言
- 响应体全文附件

Jenkins 每次构建自动生成并归档 Allure 报告。

### 9. Jenkins CI + 企微通知

Jenkinsfile 定义完整流水线,内置两种触发策略:

| 触发方式 | 表达式 | 说明 |
|---|---|---|
| 轮询 SCM | `pollSCM('H/5 * * * *')` | 每5分钟检查仓库,有新提交才触发构建 |
| 定时构建 | `cron('0 2 * * *')` | 每天 02:00 全量执行 |

企微通知分两层:conftest 的 `pytest_sessionfinish` 薄钩子只负责取统计结果,消息组装与 HTTP 发送在 [core/notifier.py](core/notifier.py)(纯函数,便于扩展钉钉/邮件渠道);内容含项目名 / 构建号 / 开始时间 / 耗时 / 通过-失败-跳过统计;构建失败 `@all`,成功静默通知;未配 `WECHAT_WEBHOOK` 则静默跳过。

## 用例覆盖矩阵

共 42 条用例,覆盖 GoREST 四大资源模块的正向 CRUD 与负向边界。

### Happy Path(24 条)

每模块 6 条:列表查询 → 详情查询 → 创建 → 更新 → 删除 → 验证已删除。

| 模块 | 用例数 |
|---|---|
| users | 6 |
| posts | 6 |
| comments | 6 |
| todos | 6 |

### 负向用例(18 条)

| 类别 | 条数 | 覆盖场景 |
|---|---|---|
| 401 鉴权失败 | 1 | POST 无 token |
| 404 资源不存在 | 6 | GET/PATCH/DELETE users、GET posts/comments/todos 不存在 ID |
| 422 字段缺失 | 2 | 缺 name / 缺 email |
| 422 枚举非法 | 3 | gender / status / todos status 非法值 |
| 422 格式非法 | 1 | email 格式非法 |
| 422 关联缺失 | 2 | posts 缺 title / comments 缺 post_id |
| 422 邮箱已占用 | 3 | 创建占位用户 → 重复邮箱 → 清理(含 setup/cleanup 链路) |

## 运行结果

```text
tests/test_users.py::test_api[查询用户列表] PASSED
tests/test_users.py::test_api[创建新用户] PASSED
tests/test_users.py::test_api[负向-无token创建用户] PASSED
tests/test_users.py::test_api[负向-创建用户缺name] PASSED
tests/test_users.py::test_api[负向-用已占用邮箱创建用户] PASSED
...
[提取] created_user_id = 8627078
[CLEANUP注册] users/8627078
...
[CLEANUP] session 结束，兜底清理 5 个资源
  [CLEANUP] users/8627105 -> 404
  ...

======================= 42 passed in 186.18s =======================

[NOTIFY] Wechat sent successfully
```

## 扩展方向

- [ ] 失败自动重试(pytest-rerunfailures)
- [ ] 日志模块(logging + 按日期切分)
- [ ] 测试覆盖率统计(pytest-cov)
- [ ] 多环境并行运行(pytest-xdist)
