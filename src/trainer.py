"""
# -*- coding: utf-8 -*-
@File    : trainer.py
@Author  : admin1
@Date    : 2025/8/18 13:59
@Description : 练习逻辑实现
"""
from src.database import QuestionDB


class InterviewTrainer:
    def __init__(self):
        self.db = QuestionDB()
        self.session_records = []

    def initialize_database(self):
        """初始化数据库"""
        self.db.initialize_database()

    def get_next_question(self):
        """获取下一个练习题目"""
        return self.db.get_question_fro_review()

    def submit_answer(self, question_id, user_answer, rating):
        """提交答案并更新复习状态"""
        record_id = self.db.save_review_record(question_id, user_answer, rating)
        if record_id:
            self.session_records.append(record_id)
        return record_id

    def get_session_summary(self):
        """获取本次训练摘要"""
        return {
            'question_reviewed': len(self.session_records),
            'session_record': self.session_records
        }

    def get_overall_stats(self):
        return self.db.get_review_status()

    def add_question(self, question, answer='', category='', difficulty='中等'):
        """添加新题目"""
        return self.db.add_question(question, answer, category, difficulty)

    def close(self):
        """关闭资源"""
        self.db.close()
