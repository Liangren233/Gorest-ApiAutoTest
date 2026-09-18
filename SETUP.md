# 本地环境配置需求文档

他人 clone 本项目后,按本清单逐项完成配置即可运行全部测试。

## 1. 环境要求

| 项 | 版本 | 用途 | 是否必须 |
|---|---|---|---|
| Python | 3.12+ | 测试引擎 | 必须 |
| Git | 任意 | 克隆仓库 | 必须 |
| pip | 随 Python | 安装依赖 | 必须 |
| Allure CLI | 2.x | 本地查看可视化报告 | 可选 |

校验:
```bash
python --version    # 期望: Python 3.12.x
git --version
```

## 2. 获取 GoREST API Token

测试目标 GoREST 需要 Bearer Token 鉴权,Token 必须自行申请:

1. 访问 https://gorest.co.in/api-register
2. 注册账号并登录
3. 进入 Personal Access Tokens 页面,点击生成新 Token
4. 复制 Token 字符串(形如 `67a99a9882d8...`)

> Token 属于个人凭据,**切勿提交到 Git**。

## 3. 克隆仓库并安装依赖

```bash
git clone https://gitee.com/liangren2334/api-auto-test.git
cd Gorest-ApiAutoTest-test
pip install -r requirements.txt
```

依赖清单见 `requirements.txt`:requests、pyyaml、pytest、allure-pytest、jsonpath、jsonschema、python-dotenv。

## 4. 配置 Token(本地)

项目根目录创建 `.env` 文件(已被 `.gitignore` 忽略,不会被提交):

```bash
# .env
GOREST_TOKEN=你刚才申请的Token
```

`ApiClient` 启动时通过 `python-dotenv` 自动加载 `.env`,读取 `GOREST_TOKEN` 注入到每个请求的 `Authorization: Bearer <token>` 头。

## 5. 运行测试

```bash
pytest
```

期望结果:`42 passed`,控制台末尾打印 `[NOTIFY] Wechat sent successfully`(若配了企微 Webhook,本地不配则静默跳过)。

## 6. 查看测试报告(可选)

需先安装 Allure CLI(见 https://allurereport.org/docs/install/):

```bash
allure serve report/tmp
```

浏览器自动打开分层报告,每个用例含:请求信息、变量池、断言、响应体附件。

## 配置校验清单

逐项确认,全部勾选即可保证本地可跑通:

- [ ] Python 3.12+ 已安装(`python --version` 输出 ≥ 3.12)
- [ ] `pip install -r requirements.txt` 无报错
- [ ] 根目录存在 `.env` 文件,内含 `GOREST_TOKEN=<有效Token>`
- [ ] Token 有效(可在 https://gorest.co.in/my-account 验证未过期)
- [ ] `pytest` 命令执行后输出 `42 passed`
- [ ] (可选) `allure --version` 能正常输出版本号

## 常见问题

**Q: 运行 pytest 报 401 Authentication failed**
A: `.env` 未创建或 Token 无效,检查 `GOREST_TOKEN` 是否正确。

**Q: 运行 pytest 报 422 / 邮箱已占用**
A: 短时间内重复运行导致邮箱冲突,等待几分钟或更换 Token 账号后重试。框架已用毫秒级时间戳 + session 级 cleanup 兜底清理,正常情况下不会残留。

**Q: 控制台中文用例名显示为 `\u8d1f\u5411` 转义字符**
A: 已在 `pytest.ini` 配置 `disable_test_id_escaping_and_forfeit_all_rights_to_community_support = true` 修复,若仍异常请确认 pytest 版本 ≥ 7.0。

**Q: 企微通知未发送**
A: 本地默认不配 `WECHAT_WEBHOOK` 环境变量,通知模块静默跳过,属正常行为。CI 上由 Jenkins 凭据 `wechat-webhook` 注入。
