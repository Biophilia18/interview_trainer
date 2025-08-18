"""
# -*- coding: utf-8 -*-
@File    : database.py
@Author  : admin1
@Date    : 2025/8/18 10:37
@Description : 数据库初始化和数据操作
"""
import pymysql
from pymysql.cursors import DictCursor

from config.db_config import DB_CONFIG
from src.scheduler import ReviewScheduler
#
# INIT_SQL = """
#     CREATE DATABASE IF NOT EXISTS interview_trainer DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
#
#     USE interview_trainer;
#
#     CREATE TABLE IF NOT EXISTS questions (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         question TEXT NOT NULL,
#         answer TEXT,
#         category VARCHAR(100),
#         difficulty ENUM('简单','中等','困难'),
#         level TINYINT DEFAULT 0 COMMENT ‘掌握程度(0-5)’,
#         last_reviewed DATETIME,
#         next_review DATETIME,
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#         INDEX idx_category (category),
#         INDEX idx_difficulty (difficulty),
#         INDEX idx_next_review (next_review)
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
#
#     CREATE TABLE IF NOT EXISTS review_records (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         question_id INT NOT NULL,
#         user_answer TEXT,
#         rating TINYINT COMMENT '用户自评掌握程度(1-5)',
#         reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#         FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
# """


class QuestionDB:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        """连接到数据库"""
        try:
            self.conn = pymysql.connect(**DB_CONFIG)
            print(f"数据库连接成功")
        except Exception as e:
            print(f"数据库连接失败 : {str(e)}")
            raise

    def initialize_database(self):
        """初始化数据库"""
        if not self.conn or not self.conn.open:
            print("数据库未连接，无法初始化")
            raise
        try:
            cursor = self.conn.cursor()
            # 执行初始化
            # 1. 创建数据库
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS interview_trainer DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
            # 2. 选择数据库
            cursor.execute("USE interview_trainer")
            # 3. 创建questions表
            cursor.execute("""
                    CREATE TABLE IF NOT EXISTS questions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        question TEXT NOT NULL,
                        answer TEXT,
                        category VARCHAR(100),
                        difficulty ENUM('简单','中等','困难'),
                        level TINYINT DEFAULT 0 COMMENT '掌握程度(0-5)',
                        last_reviewed DATETIME,
                        next_review DATETIME,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_category (category),
                        INDEX idx_difficulty (difficulty),
                        INDEX idx_next_review (next_review)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """)
            # 4. 创建review_records表
            cursor.execute("""
                    CREATE TABLE IF NOT EXISTS review_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        question_id INT NOT NULL,
                        user_answer TEXT,
                        rating TINYINT COMMENT '用户自评掌握程度(1-5)',
                        reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """)

            self.conn.commit()
            print(f"数据库初始化完成")
        except Exception as e:
            print(f"数据库初始化失败：{str(e)}")
            if self.conn:
                self.conn.rollback()
            return False

    def add_question(self, question, answer="", category="", difficulty="中等"):
        """添加新题目"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO questions (question, answer,category,difficulty)
            VALUES (%s, %s, %s, %s)
            ''', (question, answer, category, difficulty))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"添加题目失败：{str(e)}")
            self.conn.rollback()
            return None

    def get_question_fro_review(self):
        """获取复习的题目（基于间隔重复算法）"""
        try:
            cursor = self.conn.cursor(DictCursor)
            # 优先选择待复习题目，其次选择新题
            cursor.execute('''
            SELECT * FROM questions
            WHERE next_review <= NOW() OR next_review IS NULL
            ORDER BY next_review ASC, RAND()
            LIMIT 1            
            ''')
            return cursor.fetchone()
        except Exception as e:
            print(f"获取题目失败：{str(e)}")
            return None

    def save_review_record(self, question_id, user_answer, rating):
        """保存答题记录并更新题目状态"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO review_records (question_id, user_answer, rating)
            VALUES (%s, %s, %s)
            ''', (question_id, user_answer, rating))
            # 更新题目复习状态
            self._update_question_level(question_id, rating)
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"保存记录失败：{str(e)}")
            self.conn.rollback()
            return None

    def _update_question_level(self, question_id, rating):
        "根据自评分更新题目掌握情况和复习计划"
        try:
            cursor = self.conn.cursor(DictCursor)
            # 获取当前题目状态
            cursor.execute('''
            SELECT level FROM questions WHERE id = %s
            ''', (question_id,))
            question = cursor.fetchone()
            if not question:
                return
            current_level = question['level']
            new_level = ReviewScheduler.update_question_level(current_level, rating)
            next_level = ReviewScheduler.calculate_next_review(new_level)
            # 更新题目
            cursor.execute('''
            UPDATE questions
            SET level = %s, last_reviewed = NOW(), next_review = %s
            WHERE id = %s
            ''', (new_level, next_level, question_id))
        except Exception as e:
            print(f"更新题目状态失败：{str(e)}")
            raise

    def get_review_status(self):
        """获取复习统计数据"""
        try:
            cursor = self.conn.cursor(DictCursor)
            # 各级别题目数量
            cursor.execute('''
            SELECT level, COUNT(*) as count
            FROM questions
            GROUP BY level
            ''')
            level_status = {row['level']: row['count'] for row in cursor.fetchall()}
            # 今日复习数量
            cursor.execute('''
            SELECT COUNT(*) as count
            FROM review_records
            WHERE DATE(reviewed_at) = CURDATE()
            ''')
            today_count = cursor.fetchone()['count']
            # 按分类统计
            cursor.execute('''
            SELECT q.category, COUNT(*) as count
            FROM review_records r
            JOIN questions q ON r.question_id = q.id
            GROUP BY q.category
            ''')
            category_stats = {row['category']: row['count'] for row in cursor.fetchall()}
            # 按难度统计
            cursor.execute('''
            SELECT q.difficulty, COUNT(*) as count
            FROM review_records r
            JOIN questions q ON r.question_id = q.id
            GROUP BY q.difficulty
            ''')
            difficulty_stats = {row['difficulty']: row['count'] for row in cursor.fetchall()}
            return {
                'level_stats': level_status,
                'today_reviews': today_count,
                'category_stats': category_stats,
                'difficulty_stats': difficulty_stats
            }
        except Exception as e:
            print(f"获取统计信息失败：{str(e)}")
            return {}

    def close(self):
        if self.conn:
            self.conn.close()



