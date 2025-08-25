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
from werkzeug.security import generate_password_hash, check_password_hash


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
                        user_id INT,
                        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """)
            # 5.创建user表
            cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(150) NOT NULL UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        valid_difficulties = ["简单", "中等", "困难"]
        if difficulty not in valid_difficulties:
            difficulty = "中等"  # 使用默认值
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

    def save_review_record(self, question_id, user_answer, rating, user_id=None, duration_seconds=None):
        """保存答题记录并更新题目状态,可指定user_id"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO review_records (question_id, user_answer, rating, user_id, duration_seconds)
            VALUES (%s, %s, %s, %s, %s)
            ''', (question_id, user_answer, rating, user_id, duration_seconds))
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

    def get_review_status(self, user_id=None):
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
            # 今日复习数量：如果 user_id 指定则按 user_id 过滤
            if user_id:
                cursor.execute('''
                 SELECT COUNT(*) as count
                 FROM review_records
                 WHERE DATE(reviewed_at) = CURDATE() AND user_id = %s
                 ''', (user_id,))
                today_count = cursor.fetchone()['count']
                # 总用时 （今日）
                cursor.execute('''
                    SELECT COALESCE(SUM(duration_seconds), 0) as total_seconds FROM review_records  WHERE DATE(reviewed_at)=CURDATE() AND user_id = %s
                ''', (user_id,))
                total_seconds_today = cursor.fetchone()['total_seconds']
                # 平均用时
                cursor.execute('''
                    SELECT COALESCE(SUM(duration_seconds), 0) as avg_seconds FROM review_records  WHERE user_id = %s AND duration_seconds IS NOT NULL
                ''', (user_id,))
                avg_seconds = cursor.fetchone()['avg_seconds']
                # 分类统计（仅该用户）
                cursor.execute('''
                 SELECT q.category, COUNT(*) as cnt, COALESCE(SUM(r.duration_seconds), 0) as total_sec,
                 COALESCE(AVG(r.duration_seconds),0) as avg_sec
                 FROM review_records r
                 JOIN questions q ON r.question_id = q.id 
                 WHERE r.user_id = %s
                 GROUP BY q.category
                 ''', (user_id,))
                category_rows = cursor.fetchall()
                category_stats = {row['category']: {'count': row['cnt'], 'total_seconds': row['total_sec'], 'avg_seconds': row['avg_sec']} for row in category_rows}
                # 难度统计
                cursor.execute('''
                 SELECT q.difficulty, COUNT(*) as cnt, COALESCE(SUM(r.duration_seconds),0) as total_sec, 
                 COALESCE(AVG(r.duration_seconds),0) as avg_sec
                 FROM review_records r
                 JOIN questions q ON r.question_id = q.id
                 WHERE r.user_id = %s
                 GROUP BY q.difficulty
                 ''', (user_id,))
                difficulty_rows = cursor.fetchall()
                difficulty_stats = {row['difficulty']: {'count': row['cnt'], 'total_seconds': row['total_sec'], 'avg_seconds': row['avg_sec']} for row in difficulty_rows}
                return {
                    'level_stats':level_status,
                    'today_reviews':today_count,
                    'total_seconds_today': total_seconds_today,
                    'avg_seconds': avg_seconds,
                    'category_stats': category_stats,
                    'difficulty_stats': difficulty_stats
                }
            else:
                # 全站统计（原来的逻辑）
                cursor.execute('''
                 SELECT COUNT(*) as count
                 FROM review_records
                 WHERE DATE(reviewed_at) = CURDATE()
                 ''')
                today_count = cursor.fetchone()['count']

                cursor.execute('''
                 SELECT q.category, COUNT(*) as count
                 FROM review_records r
                 JOIN questions q ON r.question_id = q.id
                 GROUP BY q.category
                 ''')
                category_stats = {row['category']: row['count'] for row in cursor.fetchall()}

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

    def is_question_exists(self, question):
        try:
            cursor = self.conn.cursor(DictCursor)
            cursor.execute('''
            SELECT COUNT(*) AS cnt
            FROM questions 
            WHERE TRIM(LOWER(question)) = TRIM(LOWER(%s))
            ''', (question,))
            row = cursor.fetchone()
            cnt = row['cnt'] if row else 0
            return cnt > 0

        except Exception as e:
            # print(f"检查重复问题存在失败：{str(e)}")
            return False

    def create_user(self, username, password_plain):
        """创建新用户，返回新用户id,若存在则返回None"""
        try:
            if self.get_user_by_name(username):
                return None
            pwd_hash = generate_password_hash(password_plain)
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s)
            """, (username, pwd_hash))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"用户创建失败：{str(e)}")
            self.conn.rollback()
            return None

    def get_user_by_name(self, username):
        """按用户名查 user（返回 dict 或 None）"""
        try:
            cursor = self.conn.cursor(DictCursor)
            cursor.execute("""
                SELECT id, username, password_hash, created_at 
                FROM users
                WHERE username = %s
            """,(username,))
            return cursor.fetchone()
        except Exception as e:
            print(f"查询用户失败：{str(e)}")
            return None

    def verify_user(self, username, password_plain):
        """验证用户名/密码。验证成功返回 user dict（不含 password），失败返回 None"""
        try:
            user = self.get_user_by_name(username)
            if not user:
                return None
            if check_password_hash(user['password_hash'],password_plain):
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'created_at': user['created_at']
                }
            return None
        except Exception as e:
            print(f"验证用户失败：{str(e)}")
            return None

    def close(self):
        if self.conn:
            self.conn.close()
