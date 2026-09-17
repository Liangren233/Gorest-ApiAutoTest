# API 自动化测试框架
基于 pytest + YAML​ 数据驱动接口自动化测试框架，支持多环境配置、跨用例变量关联、Bearer Token 鉴权及 Allure 分层报告。
## 技术栈
| 组件 | 用途 |
|------|------|
| pytest | 测试引擎 + 参数化驱动 |
| PyYAML | 用例数据管理（数据/代码分离） |
| requests | HTTP 客户端 |
| python-dotenv | 密钥管理（.env 不落 Git） |
| Allure | 可视化测试报告 |
| GoRest API | 测试目标（Bearer Token 鉴权） |
## 快速启动
### 克隆项目
```bash git clone https://github.com/Liangren233/api-auto-test.git
cd api-auto-test

### 安装依赖
pip install -r requirements.txt

### 配置密钥（复制模板，填入 GoRest Token）
cp .env.example .env
### 编辑 .env，填入 GOREST_TOKEN=你的token

### 运行测试
pytest

### 查看 Allure 报告（需安装 Allure CLI）
allure serve report/tmp
```

## 目录结构
```text api-auto-test/
├── .env.example              # 环境变量模板
├── .gitignore                # 忽略 .env、缓存、报告
├── config/
│   └── env.yaml              # 多环境配置
├── core/
│   ├── client.py             # ApiClient：请求封装 + Bearer Token 鉴权
│   ├── yaml_util.py          # YAML 文件加载工具
│   └── assertor.py           # 断言引擎（status / schema）
├── data/
│   └── users.yaml            # 测试用例数据（YAML 驱动）
├── tests/
│   ├── conftest.py           # fixture + 参数化 + 命令行参数
│   └── test_users.py         # 测试主体（Allure 步骤装饰）
├── pytest.ini                # pytest 配置
├── requirements.txt          # 依赖清单
└── README.md
```

## 核心设计
### 1. 数据驱动
用例数据完全写在 YAML 中，与测试代码解耦：
```text- name: 查询用户列表并提取首个ID
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
通过 pytest_generate_tests 自动加载 YAML，实现参数化驱动。
### 2. 跨用例变量关联
使用 session 级 fixture 维护 vars_pool 变量池，支持 ${变量名} 语法跨用例传递数据：
```bash 
#第一条用例提取
extract:
  user_id: $.id

#第二条用例引用
url: /users/${user_id}
```
### 3. 多环境配置
config/env.yaml 定义多套环境，--env 参数切换：
pytest --env=test
pytest --env=prod
### 4. 断言引擎
支持两档断言：
status：HTTP 状态码校验
schema：响应字段存在性 + 类型校验
### 5. 密钥管理
Token 通过 .env 文件管理，使用 python-dotenv 自动加载，不进入代码仓库：
GOREST_TOKEN=your_token_here
CI/CD 环境通过 Jenkins Credentials 注入同名环境变量。
### 6. Allure 报告
每个用例自动生成分层步骤：
发送请求（含 URL）
提取变量（含变量池 JSON）
执行断言
响应体全文附件
## 运行结果
```bash
tests/test_users.py::test_api[查询用户列表并提取首个ID] PASSED
tests/test_users.py::test_api[查询提取到的ID对应的用户] PASSED
```
## 扩展方向
- [ ] 失败自动重试（pytest-rerunfailures）
- [ ] 日志模块（logging + 按日期切分）
- [ ] Jenkins Pipeline + 企微通知
- [ ] 更多业务模块（posts / comments CRUD）