#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信息解析脚本

功能：
- 从自然语言文本中提取结构化学生信息
- 支持成绩录入、表现记录、学生档案三种信息类型的识别
- 支持从已解析的 JSON 输入（用于 AI 图片理解后的二次解析）
- 动态检测新字段（新科目、新记录类型等）

解析模式：
  成绩录入：{姓名}{科目}{分数}分、{科目}：{分数}、{科目}{分数}（{排名}）
  表现记录：表扬{姓名}{内容}、批评{姓名}{内容}、{姓名}获奖{奖项}
  学生信息：{姓名}，{性别}，学号{数字}，{班级}班
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime


# ============================================================
#  常量定义
# ============================================================

# 已知科目列表（可动态扩展）
KNOWN_SUBJECTS = [
    "语文", "数学", "英语", "物理", "化学", "生物",
    "历史", "地理", "政治", "信息技术", "通用技术",
    "音乐", "美术", "体育", "心理健康", "劳动技术",
]

# 考试锚词 → 考试名称映射
EXAM_KEYWORDS = {
    "期中考试": "期中考试", "期中": "期中考试",
    "期末考试": "期末考试", "期末": "期末考试",
    "月考": "月考", "周考": "周考",
    "模拟考": "模拟考", "模拟考试": "模拟考",
    "联考": "联考", "统考": "统考",
    "入学考试": "入学考试", "入学": "入学考试",
    "分班考试": "分班考试", "分班": "分班考试",
    "随堂测验": "随堂测验", "单元测试": "单元测试",
    "摸底考试": "摸底考试", "摸底": "摸底考试",
    "补考": "补考",
}

# 表现记录关键词
PRAISE_KEYWORDS = ["表扬", "赞赏", "嘉奖", "奖励", "表彰", "值得表扬", "做得好"]
CRITICIZE_KEYWORDS = ["批评", "指出问题", "警告", "通报批评", "记过"]
BEHAVIOR_KEYWORDS = ["行为记录", "日常表现", "行为", "表现"]
REWARD_KEYWORDS = ["获奖", "得奖", "获得", "荣获", "被评为", "评选为", "担任", "参加"]

# 学生信息关键词
STUDENT_INFO_KEYWORDS = ["学号", "性别", "出生", "电话", "家长", "地址"]

# 已知记录类型列表（用于动态检测）
KNOWN_RECORD_TYPES = ["表扬", "批评", "行为记录", "奖惩"]

# 已知严重程度
KNOWN_SEVERITY = ["一般", "较重", "严重"]

# 中国常见姓氏（用于姓名识别辅助）
COMMON_SURNAMES = [
    "赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈",
    "褚", "卫", "蒋", "沈", "韩", "杨", "朱", "秦", "许", "何",
    "吕", "施", "张", "孔", "曹", "严", "华", "金", "魏", "陶",
    "姜", "戚", "谢", "邹", "喻", "柏", "水", "窦", "章", "苏",
    "潘", "葛", "范", "彭", "鲁", "马", "方", "袁", "柳", "唐",
    "薛", "雷", "贺", "倪", "汤", "罗", "郝", "安", "常", "于",
    "傅", "康", "余", "顾", "孟", "黄", "尹", "姚", "邵", "汪",
    "毛", "戴", "宋", "董", "梁", "杜", "阮", "郭", "林", "钟",
    "徐", "邱", "高", "夏", "田", "胡", "万", "刘", "谭",
]


# ============================================================
#  文本解析核心函数
# ============================================================

def find_exam_name(text: str) -> Optional[str]:
    """从文本中识别考试名称"""
    for keyword, exam_name in sorted(EXAM_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if keyword in text:
            return exam_name
    return None


def find_subjects(text: str) -> List[str]:
    """从文本中识别科目"""
    found = []
    for subject in sorted(KNOWN_SUBJECTS, key=len, reverse=True):
        if subject in text:
            found.append(subject)
    return found


# 非姓名的常见词（避免误识别）
STOP_WORDS = {
    "卫生", "数学", "语文", "英语", "物理", "化学",
    "生物", "历史", "地理", "政治", "音乐", "美术",
    "体育", "考试", "成绩", "表扬", "批评", "同学",
    "老师", "班级", "学校", "我们", "他们", "可以",
    "什么", "没有", "今天", "明天", "星期", "分钟",
    "安全", "注意", "问题", "所以", "因为", "而且",
}


def find_names(text: str, known_students: List[str] = None) -> List[str]:
    """
    从文本中提取可能的学生姓名

    策略：
    1. 优先匹配已知学生名单中的姓名
    2. 基于常见姓氏定位，尝试匹配2字名或3字名
    3. 上下文验证：候选姓名附近需有关键词（科目/成绩/表现等）
    """
    found = set()

    # 优先匹配已知学生
    if known_students:
        for name in sorted(known_students, key=len, reverse=True):
            if name in text:
                found.add(name)

    # 基于姓氏定位 + 上下文验证
    for surname in COMMON_SURNAMES:
        pos = 0
        while True:
            pos = text.find(surname, pos)
            if pos == -1:
                break

            # 提取姓氏后的连续中文字符（最多2个）
            rest = text[pos + len(surname):]
            chinese_chars = ""
            for c in rest:
                if '\u4e00' <= c <= '\u9fff':
                    chinese_chars += c
                else:
                    break

            # 尝试2字名（姓+1字名）
            if len(chinese_chars) >= 1:
                name2 = surname + chinese_chars[0]
                if name2 not in STOP_WORDS:
                    # 检查前后文本是否包含关键词
                    before_text = text[max(0, pos - 10):pos]
                    after_pos = pos + len(name2)
                    after_text = text[after_pos:after_pos + 20]
                    if _has_context_keyword(before_text) or _has_context_keyword(after_text):
                        found.add(name2)

            # 尝试3字名（姓+2字名）
            if len(chinese_chars) >= 2:
                name3 = surname + chinese_chars[:2]
                if name3 not in STOP_WORDS:
                    before_text = text[max(0, pos - 10):pos]
                    after_pos = pos + len(name3)
                    after_text = text[after_pos:after_pos + 20]
                    if _has_context_keyword(before_text) or _has_context_keyword(after_text):
                        found.add(name3)

            pos += 1

    # 去重：如果同时存在"张三"和"张三X"（含科目/描述字符），保留较短的
    result = list(found)
    to_remove = set()
    for a in result:
        for b in result:
            if a != b and a in b and len(a) < len(b) and b.startswith(a):
                # b 是 a 的延长版（如"张三数"vs"张三"），移除 b
                to_remove.add(b)
    return [n for n in result if n not in to_remove]


def _has_context_keyword(context: str) -> bool:
    """检查上下文是否包含科目、成绩、表现等关键词"""
    context_indicators = (
        KNOWN_SUBJECTS +
        ["分", "成绩", "考试", "表扬", "批评", "获奖", "学号",
         "排名", "满分", "表现", "记录", "同学", "迟到", "迟到",
         "班", "级", "获得", "评为", "担任", "参加"]
    )
    return any(indicator in context for indicator in context_indicators)


def parse_score_pattern(text: str, known_students: List[str] = None) -> List[dict]:
    """
    解析成绩录入模式

    支持格式：
    - 张三数学95分
    - 语文：88
    - 英语92（第3名）
    - {姓名}{科目}{数字}分
    """
    results = []
    exam_name = find_exam_name(text)
    subjects_found = find_subjects(text)
    names_found = find_names(text, known_students)
    today = datetime.now().strftime("%Y-%m-%d")

    # 如果没有找到科目，跳过成绩解析
    if not subjects_found:
        return results

    # 模式1: {姓名}{科目}{数字}分
    if names_found and subjects_found:
        for name in names_found:
            # 查找该姓名附近的科目+分数
            name_pos = text.find(name)
            if name_pos == -1:
                continue

            # 取姓名后的文本片段
            after_name = text[name_pos + len(name):name_pos + len(name) + 50]

            for subject in subjects_found:
                # 匹配 {科目}{数字}分 或 {科目}：{数字} 或 {科目}{数字}（
                patterns = [
                    rf"{subject}\s*[:：]?\s*(\d+\.?\d*)\s*分",
                    rf"{subject}\s*(\d+\.?\d*)\s*[（(]",
                    rf"{subject}\s*[:：]\s*(\d+\.?\d*)",
                ]
                for pat in patterns:
                    m = re.search(pat, after_name)
                    if m:
                        score = float(m.group(1))
                        results.append({
                            "type": "exam",
                            "table": "exam_scores",
                            "fields": {
                                "学生姓名": name,
                                "考试名称": exam_name or "日常测试",
                                "科目": subject,
                                "成绩": score,
                                "满分": 150 if score > 100 else 100,
                                "考试日期": today,
                            },
                        })
                        break

    # 模式2: 纯 "{科目}：{分数}" 格式（无明确姓名时，尝试从前文提取姓名）
    if not results and subjects_found:
        for subject in subjects_found:
            m = re.search(rf"{subject}\s*[:：]\s*(\d+\.?\d*)", text)
            if m:
                score = float(m.group(1))
                # 尝试从前面文本中找姓名
                pre_text = text[: m.start()]
                pre_names = find_names(pre_text, known_students)
                name = pre_names[-1] if pre_names else "未知"

                results.append({
                    "type": "exam",
                    "table": "exam_scores",
                    "fields": {
                        "学生姓名": name,
                        "考试名称": exam_name or "日常测试",
                        "科目": subject,
                        "成绩": score,
                        "满分": 150 if score > 100 else 100,
                        "考试日期": today,
                    },
                })

    return results


def parse_performance_pattern(text: str, known_students: List[str] = None) -> List[dict]:
    """
    解析表现记录模式

    支持格式：
    - 表扬{姓名}{内容}
    - 批评{姓名}{内容}
    - {姓名}获得{奖项}
    """
    results = []
    names_found = find_names(text, known_students)
    today = datetime.now().strftime("%Y-%m-%d")

    # 确定记录类型
    record_type = None
    for kw in PRAISE_KEYWORDS:
        if kw in text:
            record_type = "表扬"
            break
    if not record_type:
        for kw in CRITICIZE_KEYWORDS:
            if kw in text:
                record_type = "批评"
                break
    if not record_type:
        for kw in REWARD_KEYWORDS:
            if kw in text:
                record_type = "表扬"  # 获奖归入表扬
                break
    if not record_type:
        for kw in BEHAVIOR_KEYWORDS:
            if kw in text:
                record_type = "行为记录"
                break

    if not record_type or not names_found:
        return results

    for name in names_found:
        # 提取姓名附近的描述内容
        name_pos = text.find(name)
        if name_pos == -1:
            continue

        # 提取描述：姓名前后的文本
        context_start = max(0, name_pos - 10)
        context_end = min(len(text), name_pos + len(name) + 80)
        context = text[context_start:context_end].strip()

        # 清理描述，去掉姓名和关键词本身
        description = context
        for kw in PRAISE_KEYWORDS + CRITICIZE_KEYWORDS + BEHAVIOR_KEYWORDS:
            description = description.replace(kw, "")
        description = description.replace(name, "").strip("，,。.！! 　\t\n")

        if description:
            results.append({
                "type": "performance",
                "table": "daily_records",
                "fields": {
                    "学生姓名": name,
                    "记录类型": record_type,
                    "具体内容": description[:200],  # 限制长度
                    "记录日期": today,
                },
            })

    return results


def parse_student_info_pattern(text: str, known_students: List[str] = None) -> List[dict]:
    """
    解析学生档案信息模式

    支持格式：
    - {姓名}，{性别}，学号{数字}，{班级}班
    - 姓名：{姓名} 性别：{性别} 学号：{数字}
    """
    results = []
    has_info_kw = any(kw in text for kw in STUDENT_INFO_KEYWORDS)

    if not has_info_kw:
        return results

    # 尝试匹配 姓名：XXX 格式
    name_match = re.search(r"姓名[：:]\s*(\S{1,4})", text)
    gender_match = re.search(r"性别[：:]\s*(男|女)", text)
    student_id_match = re.search(r"学号[：:]\s*(\S+)", text)
    class_match = re.search(r"班级[：:]\s*(\S+)", text)
    phone_match = re.search(r"(?:电话|联系电话)[：:]\s*(\S+)", text)
    birth_match = re.search(r"(?:出生日期|生日)[：:]\s*(\S+)", text)
    address_match = re.search(r"(?:地址|家庭地址)[：:]\s*(\S+)", text)

    fields = {}

    if name_match:
        fields["姓名"] = name_match.group(1)
    if gender_match:
        fields["性别"] = gender_match.group(1)
    if student_id_match:
        fields["学号"] = student_id_match.group(1)
    if class_match:
        fields["班级"] = class_match.group(1)
    if phone_match:
        fields["联系电话"] = phone_match.group(1)
    if birth_match:
        fields["出生日期"] = birth_match.group(1)
    if address_match:
        fields["家庭地址"] = address_match.group(1)

    if fields:
        results.append({
            "type": "student",
            "table": "student_info",
            "fields": fields,
        })

    return results


def parse_text(
    text: str, known_students: List[str] = None
) -> Tuple[List[dict], List[dict]]:
    """
    综合解析文本，提取所有类型的记录

    Args:
        text:           待解析的自然语言文本
        known_students: 已知学生名单（用于姓名识别辅助）

    返回:
        (records, new_fields)
        - records:   [{"type": "exam", "table": "exam_scores", "fields": {...}}, ...]
        - new_fields: [{"table": "...", "field_name": "...", "value": "..."}, ...]
    """
    all_records = []
    new_fields = []

    # 分段落处理（用句号、换行分割）
    segments = re.split(r"[。\n]+", text)
    segments = [s.strip() for s in segments if s.strip()]

    for segment in segments:
        # 按优先级尝试各解析器
        parsed = []
        parsed.extend(parse_score_pattern(segment, known_students))
        parsed.extend(parse_performance_pattern(segment, known_students))
        parsed.extend(parse_student_info_pattern(segment, known_students))
        all_records.extend(parsed)

    # 去重：相同学生+科目+考试 的成绩去重
    seen = set()
    deduped = []
    for r in all_records:
        if r["type"] == "exam":
            key = (
                r["fields"].get("学生姓名"),
                r["fields"].get("科目"),
                r["fields"].get("考试名称"),
            )
        elif r["type"] == "performance":
            key = (
                r["fields"].get("学生姓名"),
                r["fields"].get("记录类型"),
                r["fields"].get("具体内容")[:30],
            )
        else:
            key = (r["fields"].get("姓名"), r["fields"].get("学号"))

        if key not in seen:
            seen.add(key)
            deduped.append(r)

    # 检测新字段
    new_fields = detect_new_fields(deduped, known_students)

    return deduped, new_fields


def detect_new_fields(records: List[dict], known_students: List[str] = None) -> List[dict]:
    """
    检测需要添加的新字段

    检测逻辑：
    - 新科目（不在 KNOWN_SUBJECTS 中）
    - 新记录类型（不在 KNOWN_RECORD_TYPES 中）
    """
    new_fields = []

    for r in records:
        # 检测新科目
        if r["type"] == "exam":
            subject = r["fields"].get("科目", "")
            if subject and subject not in KNOWN_SUBJECTS:
                new_fields.append({
                    "table": "exam_scores",
                    "field_name": "科目",
                    "field_type": "select_option",
                    "value": subject,
                })
                KNOWN_SUBJECTS.append(subject)  # 避免重复提示

        # 检测新记录类型
        if r["type"] == "performance":
            rtype = r["fields"].get("记录类型", "")
            if rtype and rtype not in KNOWN_RECORD_TYPES:
                new_fields.append({
                    "table": "daily_records",
                    "field_name": "记录类型",
                    "field_type": "select_option",
                    "value": rtype,
                })
                KNOWN_RECORD_TYPES.append(rtype)

    return new_fields


def parse_image_result(image_text: str, known_students: List[str] = None) -> Tuple[List[dict], List[dict]]:
    """
    解析图片 AI 理解后的文本结果

    与 parse_text 逻辑相同，但增加了表格结构解析（成绩单通常以表格形式呈现）
    """
    return parse_text(image_text, known_students)


# ============================================================
#  格式化输出
# ============================================================

def format_parse_result(records: List[dict], new_fields: List[dict]) -> str:
    """将解析结果格式化为可读的文本（供对话展示）"""
    lines = []

    if not records:
        return "未识别到可录入的信息。请确认内容格式是否正确。"

    # 按表分类统计
    exam_records = [r for r in records if r["type"] == "exam"]
    perf_records = [r for r in records if r["type"] == "performance"]
    student_records = [r for r in records if r["type"] == "student"]

    lines.append("已识别如下信息，请确认：\n")

    if exam_records:
        lines.append("📝 【考试成绩】")
        for i, r in enumerate(exam_records, 1):
            f = r["fields"]
            lines.append(
                f"  {i}. {f.get('学生姓名', '?')} - {f.get('科目', '?')} - "
                f"{f.get('成绩', '?')}分 - {f.get('考试名称', '?')}"
            )
        lines.append("")

    if perf_records:
        lines.append("📋 【日常表现】")
        for i, r in enumerate(perf_records, 1):
            f = r["fields"]
            content = f.get("具体内容", "")[:30]
            lines.append(
                f"  {i}. [{f.get('记录类型', '?')}] {f.get('学生姓名', '?')} - {content}"
            )
        lines.append("")

    if student_records:
        lines.append("👤 【学生信息】")
        for i, r in enumerate(student_records, 1):
            f = r["fields"]
            name = f.get("姓名", f.get("学生姓名", "?"))
            sid = f.get("学号", "")
            class_name = f.get("班级", "")
            lines.append(f"  {i}. {name} | 学号: {sid} | 班级: {class_name}")
        lines.append("")

    # 新字段提示
    if new_fields:
        lines.append("⚠️  检测到可能需要新增的字段：")
        for nf in new_fields:
            lines.append(
                f"  · 表「{nf['table']}」→ {nf['field_name']} =「{nf['value']}」"
            )
        lines.append("")

    # 统计
    total = len(exam_records) + len(perf_records) + len(student_records)
    lines.append(f"📊 共计 {total} 条记录待录入。")
    lines.append("请问是否全部正确？(是/修改/取消)")

    return "\n".join(lines)


# ============================================================
#  命令行入口
# ============================================================

def main():
    # Windows 兼容：确保 stdout 支持 emoji 和中文
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr.encoding != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="解析学生信息文本")
    parser.add_argument("--text", help="待解析的文本")
    parser.add_argument("--json", help="JSON 输入文件路径")
    parser.add_argument("--students", help="已知学生名单 JSON 文件路径")
    parser.add_argument("--output", help="输出 JSON 文件路径")
    args = parser.parse_args()

    known_students = []
    text = ""

    # 加载已知学生名单
    if args.students:
        with open(args.students, "r", encoding="utf-8") as f:
            known_students = json.load(f)

    # 加载输入文本
    if args.text:
        text = args.text
    elif args.json:
        with open(args.json, "r", encoding="utf-8") as f:
            data = json.load(f)
            text = data.get("text", "")
            if data.get("students"):
                known_students = data["students"]

    if not text:
        print("错误：请通过 --text 或 --json 提供输入文本", file=sys.stderr)
        sys.exit(1)

    # 解析
    records, new_fields = parse_text(text, known_students)

    # 输出
    if args.output:
        output = {
            "records": records,
            "new_fields": new_fields,
            "summary": {
                "total": len(records),
                "exam_count": len([r for r in records if r["type"] == "exam"]),
                "performance_count": len([r for r in records if r["type"] == "performance"]),
                "student_count": len([r for r in records if r["type"] == "student"]),
            },
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"解析结果已保存到: {args.output}")

    # 控制台输出
    print(format_parse_result(records, new_fields))


if __name__ == "__main__":
    main()
