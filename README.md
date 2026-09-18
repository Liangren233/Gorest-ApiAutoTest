# Gorest接口自动化测试框架

基于 pytest + YAML 数据驱动接口自动化测试框架，支持跨用例变量关联、Bearer Token 鉴权、Allure 分层报告及 Jenkins + 企微通知。

## 技术栈

| 组件 | 用途 |
|------|------|
| pytest 9.x | 测试引擎 + 参数化驱动 |
| PyYAML | 用例数据管理（数据/代码分离） |
| requests | HTTP 客户端 |
| jsonschema | 响应结构校验 |
| jsonpath | JSON 响应字段提取 |
| Allure | 可视化测试报告 |
| GoRest API | 测试目标（Bearer Token 鉴权） |
| Jenkins | CI/CD 流水线 |
| 企微 Webhook | 构建结果实时通知 |

## 快速启动

### 克隆项目
```bash
#gitee仓库(由于网络代理原因，建议优先使用gitee仓库地址，对国内更友好)
git clone https://gitee.com/liangren2334/api-auto-test.git
cd Gorest-ApiAutoTest-test

#github仓库（后续会尝试让Jenkins正常连接github仓库......)
git clone https://gitub.com/liangren233/api-auto-test.git
cd Gorest-ApiAutoTest-test
```

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置
### Token 
通过环境变量注入，本地开发可创建 `.env`：
```bash
# .env（不提交 Git）
GOREST_TOKEN=your_token_here
```

### 本地运行测试
```
pytest
```

### 本地查看 Allure 报告（需安装 Allure CLI）
```bash
allure serve report/tmp
```

### Jenkins 快速配置

#### 1. 安装插件（Manage Jenkins → Plugins → Available）

| 插件名 | 用途 |
|--------|------|
| Git Plugin | 源码拉取基础依赖 |
| Pipeline | 流水线引擎（读取 `Jenkinsfile`） |
| Credentials Binding | 将凭据注入为环境变量 |
| Allure Jenkins Plugin | 生成并归档 Allure 报告 |
| Gitee Plugin | 按需：仓库在 Gitee 且需 Webhook 自动触发时安装 |

#### 2. 配置凭据（Manage Jenkins → Credentials → System → Global）

| 凭据 ID | 类型 | 说明 |
|---------|------|------|
| `gorest-token` | Secret Text | GoRest API 的 Bearer Token |
| `wechat-webhook` | Secret Text | 企微群机器人 Webhook 地址（不配则通知静默跳过） |

> ⚠️ 凭据 ID **必须与此完全一致**，代码中通过 `withCredentials` 绑定同名变量。

#### 3. 配置 Allure 命令行（Manage Jenkins → Tools）

- 找到 **Allure Commandline** 部分
- 点击 Add Allure Commandline
- 起个名字（如 `allure`），勾选 **Install automatically**（或指定本地路径）
- 保存

#### 4. 创建 Pipeline Job

1. New Item → 输入名称 → 选 **Pipeline** → OK
2. 下滑到 **Pipeline** 配置区
3. Definition 选 **Pipeline script from SCM**
4. SCM 选 **Git**（Gitee 仓库选 **Gitee**，需先装 Gitee Plugin）
5. Repository URL 填你的仓库地址（如 `https://gitee.com/liangren2334/Gorest-ApiAutoTest`）
6. Credentials 选有权限拉代码的账号（Gitee 用私人 Token）
7. Branch 填 `master`
8. Script Path 填 `Jenkinsfile`
9. 保存

#### 5. 验证
点击 Build Now，确认：\
✅ 1.构建状态为 SUCCESS\
✅ 2.构建页面出现 Allure Report​ 图标，点开可见用例报告\
✅ 3.企微群收到构建通知（配了 WECHAT_WEBHOOK 的前提下）

## 目录结构

```text
api-auto-test/
├── conftest.py               # 根目录 conftest
├── Jenkinsfile               # Jenkins Pipeline 定义：Checkout → Setup Python → Run Tests → Allure Report 归档
├── pytest.ini                # pytest 全局配置
├── requirements.txt          # Python 依赖清单
├── README.md                 # 项目说明文档
├── .env.example              # 环境变量模板：GOREST_TOKEN=your_token_here
├── .gitignore                # Git 忽略规则
├── config/
│   └── env.yaml              # 多环境 base_url 配置（test/prod）
├── core/
│   ├── client.py             # ApiClient 封装
│   ├── yaml_util.py          # YAML 加载工具
│   └── assertor.py           # 断言引擎：支持 status（HTTP 状态码）和 schema（字段存在性+类型）两档校验
├── data/
│   └── users.yaml            # 用户模块测试用例数据：YAML 驱动
├── report/
│   └── tmp/                  # Allure 原始 JSON 结果目录（自动清空重建）
└── tests/
    ├── conftest.py           # 测试层 conftest
    └── test_users.py         # 测试主体
```

## 核心设计

### 1. 数据驱动

用例数据完全写在 YAML 中，与测试代码解耦：

```yaml
- name: 查询用户列表并提取首个ID
  request:
    method: GET
    url: /users?page=1&per_page=1
  expects:
    status: 200
    schema:
      id: { type: int }
      name: { type: str }
  extract:
    user_id: $.id
```

通过 `pytest_generate_tests` 自动加载 YAML，实现参数化驱动。

### 2. 跨用例变量关联

使用 session 级 fixture 维护 `vars_pool` 变量池，支持 `${变量名}` 语法跨用例传递数据：

```yaml
# 第一条用例提取
extract:
  user_id: $.id

# 第二条用例引用
url: /users/${user_id}
```

### 3. 断言引擎

支持两档断言：
- **status**：HTTP 状态码校验
- **schema**：响应字段存在性 + 类型校验（基于 jsonschema）

### 4. 密钥管理

Token 通过环境变量 `GOREST_TOKEN` 管理：
- 本地：`.env` 文件（已加入 `.gitignore`）
- CI：`Jenkins Credentials` 自动注入同名环境变量

### 5. Allure 报告

每个用例自动生成分层步骤：
- 发送请求（含 URL）
- 提取变量（含变量池 JSON）
- 执行断言
- 响应体全文附件

Jenkins 每次构建自动生成并归档 Allure 报告。

### 6. Jenkins + 企微通知

- Jenkins Pipeline 驱动完整 CI 流程：Checkout → Setup Python → Run Tests → Allure Report
- `tests/conftest.py` 通过 `pytest_sessionfinish` 钩子发送企微通知
- 通知内容：项目名、构建号、开始时间、耗时、通过/失败/跳过统计
- 构建失败时 `@all` 提醒，成功静默通知
- 通知模块自动从 `WECHAT_WEBHOOK` 环境变量读取 Webhook 地址，未配置则静默跳过

## 运行结果

```text
tests/test_users.py::test_api[查询用户列表并提取首个ID] PASSED
tests/test_users.py::test_api[查询提取到的ID对应的用户] PASSED

============================== 2 passed in 7.87s ==============================

[NOTIFY] Wechat sent successfully
```

## 扩展方向

- [ ] 失败自动重试（pytest-rerunfailures）
- [ ] 日志模块（logging + 按日期切分）
- [ ] 更多业务模块（posts / comments CRUD）
- [ ] 测试覆盖率统计
```