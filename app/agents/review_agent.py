"""报告审核 LangGraph Agent - 五步审核工作流"""

import json
import asyncio
from typing import TypedDict, AsyncGenerator
from langchain_core.prompts import ChatPromptTemplate
from dashscope import Generation
from app.models.llm import get_text_llm
from app.config import get_settings
from app.services.document_parser import parse_table_to_text


class ReviewState(TypedDict):
    application_text: str
    split_table_text: str
    report_text: str
    consistency_issues: list
    compliance_issues: list
    completeness_issues: list
    cnas_cma_issues: list
    standard_version_issues: list
    final_report: str


def _parse_json_array(text: str) -> list:
    """从LLM输出中解析JSON数组"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def run_review(application_text: str, split_table_text: str, report_text: str) -> dict:
    """执行五步报告审核工作流"""
    llm = get_text_llm()
    result = {
        "consistency_issues": [],
        "compliance_issues": [],
        "completeness_issues": [],
        "cnas_cma_issues": [],
        "standard_version_issues": [],
        "final_report": "",
    }

    # Step 1: 一致性审核
    try:
        prompt = ChatPromptTemplate.from_template("""
你是一名资深审核员。请对比申请表与报告内容，检查是否存在不一致。

申请表信息：
{application}

报告内容：
{report}

请以 JSON 数组格式输出问题，每项包含 field/expected/actual/severity。如无问题输出 []。
""")
        chain = prompt | llm
        r = chain.invoke({"application": application_text, "report": report_text})
        result["consistency_issues"] = _parse_json_array(r.content)
    except Exception:
        pass

    # Step 2: 标准合规审核
    try:
        prompt = ChatPromptTemplate.from_template("""
你是一名资深审核员。请根据拆分表审核报告中的检测项目是否完整合规。

拆分表：
{split_table}

报告内容：
{report}

请以 JSON 数组格式输出合规问题。如无问题输出 []。
""")
        chain = prompt | llm
        r = chain.invoke({"split_table": split_table_text, "report": report_text})
        result["compliance_issues"] = _parse_json_array(r.content)
    except Exception:
        pass

    # Step 3: 数据完整性审核
    try:
        prompt = ChatPromptTemplate.from_template("""
你是一名资深审核员。请审核报告中的数据是否完整。

申请表：{application}
拆分表：{split_table}
报告内容：{report}

请以 JSON 数组格式输出遗漏项。如无问题输出 []。
""")
        chain = prompt | llm
        r = chain.invoke({
            "application": application_text,
            "split_table": split_table_text,
            "report": report_text,
        })
        result["completeness_issues"] = _parse_json_array(r.content)
    except Exception:
        pass

    # Step 4: CNAS/CMA 合规审核
    try:
        prompt = ChatPromptTemplate.from_template("""
你是一名质量主管，熟悉 ISO/IEC 17025。
请审核以下检测报告是否符合 CNAS/CMA 报告格式要求：

【审核要点】
1. 报告是否包含资质标识（CNAS L7462 / CMA 2016192581Z / CPSC 1517）
2. 报告编号格式是否规范
3. 检测条件、日期是否完整
4. 检测依据的标准编号是否明确
5. 检测结果是否有明确判定结论（Pass/Fail/NA）
6. 是否包含免责声明和样品描述

报告内容：
{report}

请以 JSON 数组格式输出问题（field/description/severity）。如无问题输出 []。
""")
        chain = prompt | llm
        r = chain.invoke({"report": report_text})
        result["cnas_cma_issues"] = _parse_json_array(r.content)
    except Exception:
        pass

    # Step 5: 标准版本有效性审核
    try:
        prompt = ChatPromptTemplate.from_template("""
你是一名标准管理员。请检查报告中引用的检测标准是否现行有效。

常见替代关系：IEC 62368-1替代IEC 60950-1, GB 4943.1替代GB 4943, RoHS 2.0替代RoHS 1.0

报告内容：
{report}

请以 JSON 数组格式输出标准版本问题（standard/issue/suggestion）。如无问题输出 []。
""")
        chain = prompt | llm
        r = chain.invoke({"report": report_text})
        result["standard_version_issues"] = _parse_json_array(r.content)
    except Exception:
        pass

    # 生成汇总审核报告
    try:
        prompt = ChatPromptTemplate.from_template("""
你是一名资深审核员。请根据以下五类审核结果生成审核报告。

1. 一致性审核：{consistency}
2. 合规性审核：{compliance}
3. 完整性审核：{completeness}
4. CNAS/CMA合规：{cnas_cma}
5. 标准版本有效性：{standard_version}

请输出：
1. 审核结论（通过/需修改/不通过）
2. 问题汇总清单（按严重程度分类）
3. 具体修改建议
""")
        chain = prompt | llm
        r = chain.invoke({
            "consistency": json.dumps(result["consistency_issues"], ensure_ascii=False),
            "compliance": json.dumps(result["compliance_issues"], ensure_ascii=False),
            "completeness": json.dumps(result["completeness_issues"], ensure_ascii=False),
            "cnas_cma": json.dumps(result["cnas_cma_issues"], ensure_ascii=False),
            "standard_version": json.dumps(result["standard_version_issues"], ensure_ascii=False),
        })
        result["final_report"] = r.content
    except Exception as e:
        result["final_report"] = f"审核报告生成失败: {str(e)}"

    # 计算总问题数
    total = sum(
        len(result.get(k, []))
        for k in ["consistency_issues", "compliance_issues", "completeness_issues",
                   "cnas_cma_issues", "standard_version_issues"]
    )
    result["total_issues"] = total

    # 自动判定结论
    if total == 0:
        result["conclusion"] = "通过"
    elif total <= 3:
        result["conclusion"] = "需修改"
    else:
        result["conclusion"] = "不通过"

    return result


async def stream_review(
    application_text: str, split_table_text: str, report_text: str
) -> AsyncGenerator[str, None]:
    """流式报告审核：逐步发送审核进度 + 流式输出最终报告"""
    settings = get_settings()
    llm = get_text_llm()
    result = {
        "consistency_issues": [],
        "compliance_issues": [],
        "completeness_issues": [],
        "cnas_cma_issues": [],
        "standard_version_issues": [],
    }

    steps = [
        ("consistency_issues", "一致性审核", f"对比申请表与报告内容，检查是否存在不一致。\n\n申请表信息：\n{application_text}\n\n报告内容：\n{report_text}\n\n请以 JSON 数组格式输出问题，每项包含 field/expected/actual/severity。如无问题输出 []。"),
        ("compliance_issues", "标准合规审核", f"根据拆分表审核报告中的检测项目是否完整合规。\n\n拆分表：\n{split_table_text}\n\n报告内容：\n{report_text}\n\n请以 JSON 数组格式输出合规问题。如无问题输出 []。"),
        ("completeness_issues", "数据完整性审核", f"审核报告中的数据是否完整。\n\n申请表：{application_text}\n拆分表：{split_table_text}\n报告内容：{report_text}\n\n请以 JSON 数组格式输出遗漏项。如无问题输出 []。"),
        ("cnas_cma_issues", "CNAS/CMA 合规审核", f"审核以下检测报告是否符合 CNAS/CMA 报告格式要求（CNAS L7462 / CMA 2016192581Z / CPSC 1517），检查资质标识、编号格式、检测条件、标准编号、判定结论、免责声明等。\n\n报告内容：\n{report_text}\n\n请以 JSON 数组格式输出问题（field/description/severity）。如无问题输出 []。"),
        ("standard_version_issues", "标准版本有效性审核", f"检查报告中引用的检测标准是否现行有效。常见替代关系：IEC 62368-1替代IEC 60950-1, GB 4943.1替代GB 4943, RoHS 2.0替代RoHS 1.0\n\n报告内容：\n{report_text}\n\n请以 JSON 数组格式输出标准版本问题（standard/issue/suggestion）。如无问题输出 []。"),
    ]

    # 逐步执行 5 个审核步骤
    for i, (key, name, instruction) in enumerate(steps, 1):
        yield f"data: {json.dumps({'type': 'step', 'step': i, 'total': 5, 'name': name}, ensure_ascii=False)}\n\n"
        try:
            prompt = ChatPromptTemplate.from_template(
                f"你是一名资深审核员。{{instruction}}"
            )
            chain = prompt | llm
            r = chain.invoke({"instruction": instruction})
            result[key] = _parse_json_array(r.content)
        except Exception:
            pass

    # 计算总问题数
    total = sum(len(v) for v in result.values())
    if total == 0:
        conclusion = "通过"
    elif total <= 3:
        conclusion = "需修改"
    else:
        conclusion = "不通过"

    yield f"data: {json.dumps({'type': 'meta', 'conclusion': conclusion, 'total_issues': total, 'issues': {k: v for k, v in result.items()}}, ensure_ascii=False)}\n\n"

    # 流式生成最终审核报告
    summary_prompt = (
        f"你是一名资深审核员。请根据以下五类审核结果生成审核报告。\n\n"
        f"1. 一致性审核：{json.dumps(result['consistency_issues'], ensure_ascii=False)}\n"
        f"2. 合规性审核：{json.dumps(result['compliance_issues'], ensure_ascii=False)}\n"
        f"3. 完整性审核：{json.dumps(result['completeness_issues'], ensure_ascii=False)}\n"
        f"4. CNAS/CMA合规：{json.dumps(result['cnas_cma_issues'], ensure_ascii=False)}\n"
        f"5. 标准版本有效性：{json.dumps(result['standard_version_issues'], ensure_ascii=False)}\n\n"
        f"请输出：\n1. 审核结论\n2. 问题汇总清单（按严重程度分类）\n3. 具体修改建议"
    )

    messages = [{"role": "system", "content": summary_prompt}]

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def _stream_worker():
        try:
            responses = Generation.call(
                model=settings.qwen_text_model,
                messages=messages,
                result_format="message",
                stream=True,
                incremental_output=True,
                api_key=settings.dashscope_api_key,
            )
            for response in responses:
                if response.status_code == 200:
                    content = response.output.choices[0].message.get("content", "")
                    if content:
                        loop.call_soon_threadsafe(queue.put_nowait, content)
        except Exception:
            pass
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    loop.run_in_executor(None, _stream_worker)

    while True:
        content = await queue.get()
        if content is None:
            break
        yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"

    yield "data: [DONE]\n\n"
