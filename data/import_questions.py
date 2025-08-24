"""
# -*- coding: utf-8 -*-
@File    : import_questions.py
@Author  : admin1
@Date    : 2025/8/18 14:10
@Description : 题目导入
"""
import csv

from src.trainer import InterviewTrainer


def import_from_csv(file_path,mode='cli'):
    """从csv文件导入题目"""
    trainer = InterviewTrainer()
    imported_cnt = 0
    skipped_cnt = 0  # 重复题目
    failed_rows = []  # 添加失败的信息
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            total_rows = 0  # 总行计数
            for _ in reader:  # 先统计行数
                total_rows += 1
            f.seek(0)  # 重置文件指针
            next(reader)  # 跳过标题行
            if mode == "cli":
                print(f"开始导入，共 {total_rows} 行")
            for line_num, row in enumerate(reader, start=2):  # 行号从2开始
                # 显示进度

                print(f"处理中： 第 {line_num}/{total_rows + 1} 行... ")

                if 'question' not in row:
                    failed_rows.append((line_num, "缺少 'question' row", row))
                    continue
                try:
                    # 导入题目
                    question = row['question'].strip()
                    # 检查题目是否已存在
                    if trainer.question_exists(question):
                        skipped_cnt += 1
                        # failed_rows.append((line_num, "题目已存在", row))
                        continue
                    answer = row.get('answer', '').strip()
                    category = row.get('category', '').strip()
                    difficulty = row.get('difficulty', '中等').strip()
                    trainer.add_question(question, answer, category, difficulty)
                    # print(f"读取的题目信息：{question}")
                    # print(f"读取的题目信息：{answer}")
                    # print(f"读取的题目信息：{category}")
                    # print(f"读取的题目信息：{difficulty}")
                    imported_cnt += 1
                except Exception as e:
                    failed_rows.append((line_num, str(e), row))
        if mode == "cli":
            print("\n" + '=' * 50)
            print(f"成功导入 {imported_cnt} 道题目")
            print(f"跳过重复 {skipped_cnt} 道题目")
            print(f"导入失败 {len(failed_rows)} 行")
            print('=' * 50)
            if failed_rows:
                for i, (line, error, data) in enumerate(failed_rows, 1):
                    print(f"#{i} 行：{line} | 错误类型：{error}")
        else: # web
            return {
            "imported": imported_cnt,
            "skipped": skipped_cnt,
            "failed": len(failed_rows),
            "failed_details": failed_rows
        }
    except Exception as e:
        if mode == "cli":
            print(f"文件处理失败：{str(e)}")
        else:
            return {"error":str(e)}
    finally:
        trainer.close()


if __name__ == '__main__':
    path = r"E:\FileMgr\questions.csv"
    import_from_csv(path,mode="cli")
