from ldap3 import Server, Connection, ALL

# 绑定服务器
server = Server('ldap://192.168.254.10',get_info=ALL)

# 创建并打开链接
conn = Connection(server)
conn.open()

# 查看连接状态
print("Connect Status:", conn.closed)
print("root DSE info",)
print(server.info)

# 取消绑定（关闭连接）
conn.unbind()