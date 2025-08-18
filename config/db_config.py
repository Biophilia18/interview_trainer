"""
# -*- coding: utf-8 -*-
@File    : db_config.py.py
@Author  : admin1
@Date    : 2025/8/18 9:21
@Description : 配置文件
"""
import pymysql

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "interview_trainer",
    "charset": "utf8mb4"
}
# try:
#     con = pymysql.connect(**DB_CONFIG)
#     print(f"connect success")
# except Exception as e:
#     print(f"连接失败 : {str(e)}")
