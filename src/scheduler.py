"""
# -*- coding: utf-8 -*-
@File    : scheduler.py
@Author  : admin1
@Date    : 2025/8/18 11:15
@Description : 问题的间隔复习算法
"""
from datetime import datetime, timedelta


class ReviewScheduler:
    interval = [0, 1, 3, 5, 7]  # 问题重复算法参数:天

    @staticmethod
    def update_question_level(current_level, rating):
        """根据自评分更新掌握级别"""
        # 调整规则
        # - 评分 4-5：升级
        # - 评分 3：保持
        # - 评分 1-2：降级
        if rating >= 4:  # 很好
            return min(5, current_level + 1)
        elif rating <= 2:  # 差
            return max(0, current_level - 1)
        else:  # 一般
            return current_level

    @staticmethod
    def calculate_next_review(level):
        """根据掌握程度计算下次复习时间"""
        if level >= len(ReviewScheduler.interval):  # 完全掌握的不安排复习
            return None
        return datetime.now() + timedelta(days=ReviewScheduler.interval[level])
