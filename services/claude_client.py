import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

FRAMEWORK = {
    "团队背景": {
        "weight": 0.25,
        "subcriteria": {
            "创始人背景与经验": 0.40,
            "团队完整性": 0.30,
            "行业专业度": 0.30,
        },
    },
    "市场规模": {
        "weight": 0.20,
        "subcriteria": {
            "TAM/SAM规模": 0.40,
            "市场增长率": 0.30,
            "竞争格局": 0.30,
        },
    },
    "产品与技术": {
        "weight": 0.20,
        "subcriteria": {
            "技术壁垒与护城河": 0.40,
            "产品差异化": 0.30,
            "产品市场契合度": 0.30,
        },
    },
    "商业模式": {
        "weight": 0.15,
        "subcriteria": {
            "收入模式清晰度": 0.40,
            "单位经济模型": 0.35,
            "可扩展性": 0.25,
        },
    },
    "牵引力": {
        "weight": 0.10,
        "subcriteria": {
            "收入/GMV增长": 0.40,
            "用户/客户增长": 0.35,
            "关键合作与背书": 0.25,
        },
    },
    "财务状况": {
        "weight": 0.05,
        "subcriteria": {
            "现金流与Runway": 0.40,
            "融资历史": 0.35,
            "估值合理性": 0.25,
        },
    },
    "退出潜力": {
        "weight": 0.05,
        "subcriteria": {
            "IPO/并购可比案例": 0.50,
            "战略价值": 0.50,
        },
    },
}

SYSTEM_PROMPT = """你是一位资深一级市场投资分析师，拥有丰富的VC/PE投资经验。
你的任务是分析创业项目材料，按照投资评估框架进行评分，并生成结构化的投资分析报告。
请严格按照要求的JSON格式输出，不要输出任何其他内容。"""

def build_user_prompt(text: str, framework: dict) -> str:
    framework_desc = json.dumps(framework, ensure_ascii=False, indent=2)
    return f"""请分析以下项目材料，并严格按照JSON格式返回完整的投资评估结果。

===项目材料===
{text[:12000]}

===评估框架===
{framework_desc}

请返回如下JSON结构（不要有任何额外文字，只返回JSON）：
{{
  "project_name": "项目名称",
  "company_name": "公司名称",
  "industry": "所处行业（详细描述）",
  "industry_tag": "行业标签（从以下选择：SaaS_B2B、消费零售、医疗健康、金融科技、硬件制造、教育科技、新能源、人工智能、电商物流、游戏娱乐、其他）",
  "stage": "融资阶段（天使/Pre-A/A/B/C轮等）",
  "summary": "项目简介（200字以内）",
  "scores": {{
    "团队背景": {{
      "subcriteria": {{
        "创始人背景与经验": {{"score": 7, "evidence": "根据材料中的具体描述"}},
        "团队完整性": {{"score": 7, "evidence": "..."}},
        "行业专业度": {{"score": 7, "evidence": "..."}}
      }}
    }},
    "市场规模": {{
      "subcriteria": {{
        "TAM/SAM规模": {{"score": 7, "evidence": "..."}},
        "市场增长率": {{"score": 7, "evidence": "..."}},
        "竞争格局": {{"score": 7, "evidence": "..."}}
      }}
    }},
    "产品与技术": {{
      "subcriteria": {{
        "技术壁垒与护城河": {{"score": 7, "evidence": "..."}},
        "产品差异化": {{"score": 7, "evidence": "..."}},
        "产品市场契合度": {{"score": 7, "evidence": "..."}}
      }}
    }},
    "商业模式": {{
      "subcriteria": {{
        "收入模式清晰度": {{"score": 7, "evidence": "..."}},
        "单位经济模型": {{"score": 7, "evidence": "..."}},
        "可扩展性": {{"score": 7, "evidence": "..."}}
      }}
    }},
    "牵引力": {{
      "subcriteria": {{
        "收入/GMV增长": {{"score": 7, "evidence": "..."}},
        "用户/客户增长": {{"score": 7, "evidence": "..."}},
        "关键合作与背书": {{"score": 7, "evidence": "..."}}
      }}
    }},
    "财务状况": {{
      "subcriteria": {{
        "现金流与Runway": {{"score": 7, "evidence": "..."}},
        "融资历史": {{"score": 7, "evidence": "..."}},
        "估值合理性": {{"score": 7, "evidence": "..."}}
      }}
    }},
    "退出潜力": {{
      "subcriteria": {{
        "IPO/并购可比案例": {{"score": 7, "evidence": "..."}},
        "战略价值": {{"score": 7, "evidence": "..."}}
      }}
    }}
  }},
  "key_highlights": ["核心亮点1", "核心亮点2", "核心亮点3"],
  "key_risks": ["主要风险1", "主要风险2", "主要风险3"],
  "investment_brief": "综合投资简报（400字以内，包含项目概况、核心优势、主要风险、投资建议）"
}}

评分标准：1-3分（严重不足），4-5分（低于平均），6-7分（达到平均），8-9分（优秀），10分（行业顶尖）
对于材料中未提及的信息，根据行业惯例给予5分并在evidence中注明"材料未提及"。"""


def calculate_weighted_score(scores: dict) -> dict:
    """Calculate weighted scores for each dimension and total."""
    result = {}
    total_weighted = 0.0

    for dim, config in FRAMEWORK.items():
        if dim not in scores:
            continue
        sub = scores[dim]["subcriteria"]
        sub_weights = config["subcriteria"]
        dim_score = sum(
            sub[k]["score"] * sub_weights[k]
            for k in sub_weights
            if k in sub
        )
        weighted = dim_score * config["weight"]
        result[dim] = {
            "raw_score": round(dim_score, 2),
            "weight": config["weight"],
            "weighted_score": round(weighted * 10, 2),  # out of 10 * weight * 10 = out of 10
            "subcriteria": sub,
        }
        total_weighted += dim_score * config["weight"]

    recommendation_map = [
        (8.5, "强烈推荐投资", "#16a34a"),
        (7.0, "建议投资", "#65a30d"),
        (5.5, "谨慎观望", "#ca8a04"),
        (4.0, "不建议投资", "#dc2626"),
        (0, "明确拒绝", "#7f1d1d"),
    ]
    rec_text, rec_color = "明确拒绝", "#7f1d1d"
    for threshold, text, color in recommendation_map:
        if total_weighted >= threshold:
            rec_text, rec_color = text, color
            break

    return {
        "dimensions": result,
        "total": round(total_weighted, 2),
        "total_pct": round(total_weighted * 10, 1),
        "recommendation": rec_text,
        "recommendation_color": rec_color,
    }


async def analyze_document(text: str, filename: str) -> dict:
    prompt = build_user_prompt(text, FRAMEWORK)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    # Strip markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    analysis = json.loads(raw)
    scoring = calculate_weighted_score(analysis["scores"])
    analysis["scoring"] = scoring
    analysis["framework"] = FRAMEWORK
    return analysis
