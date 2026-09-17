# AD-Python-ldap3-Tools

一组用于 Active Directory 日常运维与审计的 Python 脚本集合。

## 背景

这些脚本来自实际运维场景中的重复性需求：批量导出、健康巡检、权限排查、复制状态检查等。
每个工具都能独立运行，也可以组合使用。

## 工具列表

| 工具                          | 说明                                      | 状态 |
|-----------------------------|-----------------------------------------|---|
| [ldap-export](ldap-export/) | 全量导出指定 OU 下的用户与计算机，支持 xlsx / csv / json | ✅ 可用 |
| gpo                         | GPO 链接关系与权限审计                           | 🚧 计划中 |
| rid                         | 安全主体相关操作                                | 🚧 计划中 |

## 环境要求

- Python 3.10+
- 可访问 DC 的网络环境
- 一个具备读取权限的域账户

## 快速开始

```bash
git clone https://github.com/springtsuki/AD-Python-ldap3-Tools.git
cd AD-Python-ldap3-Tools
pip install -r requirements.txt
```