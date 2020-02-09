import mysql.connector

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  passwd="password",
  auth_plugin='mysql_native_password',
  database="Code211"
)

print(mydb)
