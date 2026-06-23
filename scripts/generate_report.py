#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合评价报告生成脚本（飞书 CLI 重构版）

功能：
- 接收从飞书 CLI 获取的 JSON 数据
- 学业分析：各科最高/最低/平均/趋势、强弱项识别
- 表现分析：表扬/批评/行为记录次数统计
- 生成 Markdown 格式的综合评价报告

使用：
    # 从 CLI 获取数据后保存为 JSON
    python scripts/generate_report.py --student 张三 --data /tmp/student_data.json
    python scripts/generate_report.py --student 张三 --data /tmp/student_data.json --from 2024-02-01 --to 2024-06-30

输入 JSON 格式（由 AI 从 lark-cli 输出中组装）：
{
  "student_info": [{"fields": {"姓名":"张三","学号":"202401001","性别":"男","班级":"高一(3)班"}}],
  "exam_scores": [{"fields": {"学生姓名":"张三","科目":"数学","成绩":95,"满分":100,"考试名称":"期中考试","考试日期":1710460800000}}],
  "daily_records": [{"fields": {"学生姓名":"张三","记录类型":"表扬","具体内容":"主动帮助同学打扫卫生","记录日期":1710460800000}}]
}
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

# 东八区
TZ_CN = timezone(timedelta(hours=8))


def timestamp_to_date(ts: int) -> str:
    """毫秒时间戳 → 日期字符串"""
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(ts / 1000, tz=TZ_CN).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return str(ts)


def date_to_timestamp(date_str: str) -> int:
    """日期字符串 → 毫秒时间戳"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dt = dt.replace(tzinfo=TZ_CN)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return 0


# ============================================================
#  数据分析
# ============================================================

def analyze_exam_scores(exam_records: List[dict], date_from: str = None, date_to: str = None) -> dict:
    """
    学业分析

    返回: {
        "subjects": {"数学": {"scores": [95,88,92], "max": 95, "min": 88, "avg": 91.7, "count": 3, "trend": "↑ 上升"}},
        "summary": {"strong_subjects": ["数学"], "weak_subjects": ["英语"], "total_exams": 5}
    }
    """
    if not exam_records:
        return {"subjects": {}, "summary": {"strong_subjects": [], "weak_subjects": [], "total_exams": 0, "total_subjects": 0}}

    # 时间过滤
    from_ts = date_to_timestamp(date_from) if date_from else 0
    to_ts = date_to_timestamp(date_to) if date_to else 9999999999999

    filtered = []
    for r in exam_records:
        f = r.get("fields", {})
        date_ts = f.get("考试日期", 0)
        if isinstance(date_ts, str):
            date_ts = date_to_timestamp(date_ts)
        if from_ts <= date_ts <= to_ts:
            filtered.append(r)

    if not filtered:
        return {"subjects": {}, "summary": {"strong_subjects": [], "weak_subjects": [], "total_exams": 0, "total_subjects": 0}}

    # 按科目分组
    by_subject = defaultdict(list)
    for r in filtered:
        f = r.get("fields", {})
        subject = f.get("科目", "未知")
        score = float(f.get("成绩", 0))
        full = float(f.get("满分", 100))
        normalized = (score / full * 100) if full > 0 else score
        exam_name = f.get("考试名称", "")
        date_ts = f.get("考试日期", 0)
        if isinstance(date_ts, str):
            date_ts = date_to_timestamp(date_ts)

        by_subject[subject].append({
            "score": score,
            "full": full,
            "normalized": round(normalized, 1),
            "exam": exam_name,
            "date": date_ts,
        })

    # 分析每个科目
    subjects_analysis = {}
    all_avg_scores = []

    for subject, scores in by_subject.items():
        raw_scores = [s["score"] for s in scores]
        normalized_scores = [s["normalized"] for s in scores]

        scores_sorted = sorted(scores, key=lambda s: s["date"])

        avg_raw = sum(raw_scores) / len(raw_scores) if raw_scores else 0
        avg_norm = sum(normalized_scores) / len(normalized_scores) if normalized_scores else 0

        # 趋势分析
        trend = "平稳"
        if len(scores_sorted) >= 2:
            half = max(1, len(scores_sorted) // 2)
            first_half = [s["normalized"] for s in scores_sorted[:half]]
            second_half = [s["normalized"] for s in scores_sorted[half:]]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            diff = second_avg - first_avg
            if diff > 5:
                trend = "↑ 上升"
            elif diff < -5:
                trend = "↓ 下降"
            else:
                trend = "→ 平稳"

        subjects_analysis[subject] = {
            "scores": raw_scores,
            "max": max(raw_scores),
            "min": min(raw_scores),
            "avg": round(avg_raw, 1),
            "avg_normalized": round(avg_norm, 1),
            "count": len(scores),
            "trend": trend,
            "exams": [{"name": s["exam"], "score": s["score"], "date": s["date"]} for s in scores_sorted],
        }
        all_avg_scores.append((subject, avg_norm))

    # 强弱项识别
    if all_avg_scores:
        all_avg_scores.sort(key=lambda x: x[1], reverse=True)
        strong_threshold = all_avg_scores[0][1] - 8
        weak_threshold = all_avg_scores[-1][1] + 8
        strong_subjects = [s[0] for s in all_avg_scores if s[1] >= strong_threshold]
        weak_subjects = [s[0] for s in all_avg_scores if s[1] <= weak_threshold]
    else:
        strong_subjects, weak_subjects = [], []

    return {
        "subjects": subjects_analysis,
        "summary": {
            "strong_subjects": strong_subjects,
            "weak_subjects": weak_subjects,
            "total_exams": len(filtered),
            "total_subjects": len(subjects_analysis),
        },
    }


def analyze_performance(perf_records: List[dict]) -> dict:
    """
    表现分析

    返回: {"praise_count": 8, "criticize_count": 2, "highlights": [...], "concerns": [...]}
    """
    by_type = defaultdict(list)
    for r in perf_records:
        f = r.get("fields", {})
        rtype = f.get("记录类型", "行为记录")
        by_type[rtype].append(f)

    praise_records = by_type.get("表扬", [])
    criticize_records = by_type.get("批评", [])
    behavior_records = by_type.get("行为记录", [])
    reward_records = by_type.get("奖惩", [])

    highlights = [r.get("具体内容", "") for r in (praise_records + reward_records) if r.get("具体内容")]
    concerns = [r.get("具体内容", "") for r in criticize_records if r.get("具体内容")]

    return {
        "praise_count": len(praise_records),
        "criticize_count": len(criticize_records),
        "behavior_count": len(behavior_records),
        "reward_count": len(reward_records),
        "total": len(perf_records),
        "highlights": highlights[:5],
        "concerns": concerns[:5],
        "by_type": {k: v for k, v in by_type.items()},
    }


# ============================================================
#  报告生成
# ============================================================

def generate_markdown_report(
    student_name: str,
    student_info: List[dict],
    exam_analysis: dict,
    perf_analysis: dict,
    date_from: str = None,
    date_to: str = None,
) -> str:
    """生成 Markdown 格式的综合评价报告"""
    info = student_info[0].get("fields", {}) if student_info else {}
    class_name = info.get("班级", "未知班级")
    gender = info.get("性别", "")

    today = datetime.now(TZ_CN).strftime("%Y-%m-%d")
    period = f"{date_from or '入学'} 至 {date_to or today}"

    lines = []
    lines.append("# 学生综合评价报告")
    lines.append("")
    lines.append(f"**姓名**：{student_name}　　　**性别**：{gender or '未登记'}　　　**班级**：{class_name}")
    lines.append(f"**报告周期**：{period}")
    lines.append("")

    # 一、学业表现
    lines.append("## 一、学业表现")
    lines.append("")
    subjects = exam_analysis.get("subjects", {})
    summary = exam_analysis.get("summary", {})

    if subjects:
        lines.append("### 各科成绩总览")
        lines.append("")
        lines.append("| 科目 | 考试次数 | 最高分 | 最低分 | 平均分 | 趋势 |")
        lines.append("|------|---------|--------|--------|--------|------|")
        for subject, analysis in subjects.items():
            lines.append(
                f"| {subject} | {analysis['count']} | {analysis['max']} | "
                f"{analysis['min']} | {analysis['avg']} | {analysis['trend']} |"
            )
        lines.append("")

        strong = summary.get("strong_subjects", [])
        weak = summary.get("weak_subjects", [])
        if strong:
            lines.append(f"**优势科目**：{'、'.join(strong)}")
        if weak:
            lines.append(f"**需提升科目**：{'、'.join(weak)}")
        lines.append("")

        lines.append("### 近期考试记录")
        lines.append("")
        for subject, analysis in subjects.items():
            recent = analysis.get("exams", [])[-3:]
            if recent:
                exam_strs = []
                for e in recent:
                    d = timestamp_to_date(e["date"]) if isinstance(e["date"], (int, float)) else str(e.get("date", "?"))
                    exam_strs.append(f"{e['exam']}({d})={e['score']}分")
                lines.append(f"**{subject}**：" + "、".join(exam_strs))
        lines.append("")
    else:
        lines.append("暂无考试记录。")
        lines.append("")

    # 二、行为表现
    lines.append("## 二、行为表现")
    lines.append("")
    praise = perf_analysis.get("praise_count", 0)
    criticize = perf_analysis.get("criticize_count", 0)
    behavior = perf_analysis.get("behavior_count", 0)
    reward = perf_analysis.get("reward_count", 0)
    total = perf_analysis.get("total", 0)

    lines.append(f"表扬 **{praise}** 次 | 批评 **{criticize}** 次 | 行为记录 **{behavior}** 次 | 奖惩 **{reward}** 次")
    lines.append(f"共计 **{total}** 条表现记录")
    lines.append("")

    highlights = perf_analysis.get("highlights", [])
    if highlights:
        lines.append("**亮点**：")
        for h in highlights[:3]:
            lines.append(f"- {h}")
        lines.append("")

    concerns = perf_analysis.get("concerns", [])
    if concerns:
        lines.append("**需关注**：")
        for c in concerns[:3]:
            lines.append(f"- {c}")
        lines.append("")

    # 三、综合评价
    lines.append("## 三、综合评价")
    lines.append("")
    eval_parts = []

    if strong and weak:
        eval_parts.append(
            f"{student_name}同学在{'、'.join(strong)}方面表现突出，成绩稳定。"
            f"在{'、'.join(weak)}方面需要投入更多精力，建议加强针对性练习。"
        )
    elif strong:
        eval_parts.append(
            f"{student_name}同学在各科目上表现均衡，其中{'、'.join(strong)}较为突出。"
            f"建议保持学习节奏，继续深化理解。"
        )
    elif weak:
        eval_parts.append(
            f"{student_name}同学在学业上尚有提升空间，特别是{'、'.join(weak)}科目需要额外关注。"
        )
    else:
        eval_parts.append("学业表现需通过更多考试数据来评估。")

    if praise > criticize and praise > 0:
        eval_parts.append(f"行为表现方面整体良好，获得{praise}次表扬记录，表现出积极向上的态度。")
    elif criticize > praise:
        eval_parts.append(f"行为方面有{criticize}次批评记录，需要加强自我管理意识。")
    else:
        eval_parts.append("行为表现方面需持续关注和引导。")

    if highlights:
        eval_parts.append(f"特别是在{highlights[0][:30]}等方面展现了良好的品质。")

    lines.append(" ".join(eval_parts))
    lines.append("")

    # 四、发展建议
    lines.append("## 四、发展建议")
    lines.append("")
    suggestions = []

    if weak:
        for w_subject in weak[:3]:
            suggestions.append(f"**{w_subject}**：建议每周增加专项练习时间，可寻求科任老师针对指导。")
    if criticize > 0:
        suggestions.append("**行为习惯**：建议加强时间管理和纪律意识。")
    if strong and len(strong) >= 1:
        suggestions.append(f"**拓展提升**：在优势科目（{'、'.join(strong)}）上可尝试参加学科竞赛或拓展学习。")
    if praise >= 3:
        suggestions.append("**榜样引领**：鼓励在班级中发挥积极作用。")

    if not suggestions:
        suggestions.append("建议持续保持学习状态，积极参与班级活动，全面发展。")

    for i, s in enumerate(suggestions, 1):
        lines.append(f"{i}. {s}")

    lines.append("")
    lines.append("---")
    lines.append(f"*本报告由班主任班务记录系统自动生成 | 生成时间：{today}*")

    return "\n".join(lines)


# ============================================================
#  主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="生成学生综合评价报告")
    parser.add_argument("--student", required=True, help="学生姓名")
    parser.add_argument("--data", required=True, help="JSON 数据文件路径（由飞书 CLI 获取）")
    parser.add_argument("--from", dest="date_from", help="报告开始日期 (yyyy-MM-dd)")
    parser.add_argument("--to", dest="date_to", help="报告结束日期 (yyyy-MM-dd)")
    parser.add_argument("--output", help="输出文件路径")
    args = parser.parse_args()

    # 加载数据
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 数据文件不存在: {args.data}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 格式错误: {e}", file=sys.stderr)
        sys.exit(1)

    student_info = data.get("student_info", [])
    exam_scores = data.get("exam_scores", [])
    daily_records = data.get("daily_records", [])

    if not student_info and not exam_scores and not daily_records:
        print(f"⚠️  未找到 {args.student} 的任何记录。请确认姓名是否正确。")
        sys.exit(1)

    # 分析数据
    exam_analysis = analyze_exam_scores(exam_scores, args.date_from, args.date_to)
    perf_analysis = analyze_performance(daily_records)

    # 生成报告
    report = generate_markdown_report(
        args.student,
        student_info,
        exam_analysis,
        perf_analysis,
        args.date_from,
        args.date_to,
    )

    # 输出
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"报告已保存到: {args.output}")

    print(report)


if __name__ == "__main__":
    main()
