"""
RAG Evaluation Script – RAGAS metrics
======================================
Đo lường chất lượng hệ thống RAG theo 4 tiêu chí chuẩn:

  Faithfulness        : Câu trả lời có trung thực với context không?
  Answer Relevancy    : Câu trả lời có đúng trọng tâm câu hỏi không?
  Context Precision   : Context retrieved có thực sự liên quan không?
  Context Recall      : Context có chứa đủ thông tin để trả lời không?

Yêu cầu:
  pip install ragas datasets

Chạy:
  python evaluate_rag.py --api-key sk-... --db faiss_news_db_ivf
  python evaluate_rag.py --api-key sk-... --no-hybrid   # so sánh dense-only
  python evaluate_rag.py --api-key sk-... --output results/eval_hybrid.csv
"""
from dotenv import load_dotenv

load_dotenv()

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Dict


# ─────────────────────────── TEST DATASET ────────────────────────────────────
# Tập câu hỏi mẫu – CẬP NHẬT ground_truth theo nội dung thực tế trong database
# Cấu trúc: question, ground_truth (câu trả lời kỳ vọng)
TEST_QUESTIONS: List[Dict[str, str]] = [
    # Giáo dục
    {
        "question": "Học phí đại học ở Việt Nam tăng như thế nào?",
        "ground_truth": "Học phí đại học tại Việt Nam có xu hướng tăng qua các năm, "
                       "ảnh hưởng đến nhiều sinh viên và gia đình.",
    },
    # Bất động sản
    {
        "question": "Giá nhà ở Hà Nội và TP.HCM biến động ra sao?",
        "ground_truth": "Giá bất động sản tại Hà Nội và TP.HCM có xu hướng tăng do "
                       "nhu cầu cao và nguồn cung hạn chế.",
    },
    # Lao động việc làm
    {
        "question": "Tình hình thất nghiệp và việc làm tại Việt Nam?",
        "ground_truth": "Thị trường lao động Việt Nam đang phục hồi với tỷ lệ thất nghiệp "
                       "giảm, tuy nhiên vẫn còn nhiều thách thức.",
    },
    # Du lịch
    {
        "question": "Du lịch Việt Nam phục hồi sau dịch COVID như thế nào?",
        "ground_truth": "Du lịch Việt Nam đang phục hồi mạnh mẽ với lượng khách quốc tế "
                       "và nội địa tăng đáng kể.",
    },
    # Công nghệ
    {
        "question": "Xu hướng công nghệ số và chuyển đổi số tại Việt Nam?",
        "ground_truth": "Việt Nam đang đẩy mạnh chuyển đổi số trong nhiều lĩnh vực "
                       "như hành chính, kinh tế và xã hội.",
    },
    # Kinh tế
    {
        "question": "Tăng trưởng kinh tế Việt Nam gần đây như thế nào?",
        "ground_truth": "Kinh tế Việt Nam duy trì đà tăng trưởng tích cực, "
                       "với GDP tăng trưởng ở mức khá cao so với khu vực.",
    },
    # Giao thông
    {
        "question": "Giá xăng dầu tại Việt Nam biến động ra sao?",
        "ground_truth": "Giá xăng dầu Việt Nam điều chỉnh theo thị trường thế giới, "
                       "ảnh hưởng đến chi phí sinh hoạt của người dân.",
    },
    # An sinh xã hội
    {
        "question": "Chính sách an sinh xã hội cho người lao động ở Việt Nam?",
        "ground_truth": "Việt Nam có nhiều chính sách hỗ trợ người lao động như "
                       "bảo hiểm xã hội, bảo hiểm thất nghiệp và trợ cấp.",
    },
    # Tiêu dùng
    {
        "question": "Chỉ số giá tiêu dùng CPI của Việt Nam tăng giảm thế nào?",
        "ground_truth": "CPI của Việt Nam có những biến động nhất định, "
                       "chịu ảnh hưởng của giá thực phẩm, xăng dầu và dịch vụ.",
    },
    # Ô tô xe máy
    {
        "question": "Xu hướng xe điện và xe máy điện tại Việt Nam?",
        "ground_truth": "Xe điện và xe máy điện ngày càng phổ biến tại Việt Nam "
                       "do ưu đãi chính sách và ý thức môi trường tăng cao.",
    },
]


# ─────────────────────────── RAGAS SETUP ─────────────────────────────────────

def setup_ragas_evaluator(api_key: str):
    """Khởi tạo RAGAS LLM + Embeddings – RAGAS 0.4.x API."""
    from openai import OpenAI
    from ragas.llms import llm_factory
    from ragas.embeddings import OpenAIEmbeddings   # dùng trực tiếp, không qua factory

    client = OpenAI(api_key=api_key)
    llm = llm_factory("gpt-4o-mini", client=client)
    embeddings = OpenAIEmbeddings(client=client, model="text-embedding-3-small")
    return llm, embeddings


# ─────────────────────────── COLLECT RAG OUTPUTS ─────────────────────────────

def collect_rag_outputs(
    chatbot,
    questions: List[Dict[str, str]],
    verbose: bool = True,
) -> List[Dict]:
    """
    Chạy RAG pipeline cho từng câu hỏi, thu thập:
      question, answer, contexts (list of str), ground_truth
    """
    results = []
    for i, item in enumerate(questions, 1):
        q = item["question"]
        gt = item["ground_truth"]

        if verbose:
            print(f"\n[{i}/{len(questions)}] Query: '{q}'")

        start = time.time()
        try:
            rag_result, used_k = chatbot.enhanced_search(q)
            elapsed = time.time() - start

            answer = rag_result["answer"]
            contexts = [doc.page_content for doc in rag_result["context"]]

            if verbose:
                print(f"  ✅ Answer ({elapsed:.1f}s, {used_k} docs): {answer[:120]}...")
                for j, ctx in enumerate(contexts, 1):
                    print(f"  📄 Context {j}: {ctx[:80]}...")

            results.append({
                "question":     q,
                "answer":       answer,
                "contexts":     contexts,
                "ground_truth": gt,
                "used_k":       used_k,
                "latency_s":    round(elapsed, 2),
            })

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "question":     q,
                "answer":       f"ERROR: {e}",
                "contexts":     [],
                "ground_truth": gt,
                "used_k":       0,
                "latency_s":    -1,
            })

    return results


# ─────────────────────────── RUN RAGAS ───────────────────────────────────────

def run_ragas_evaluation(
    rag_outputs: List[Dict],
    api_key: str,
) -> Dict:
    """
    Chạy RAGAS evaluation, trả về dict kết quả metric.
    Dùng RAGAS 0.4.x API: EvaluationDataset + instantiated metric objects.
    """
    from ragas import evaluate, EvaluationDataset, SingleTurnSample
    from ragas.metrics.collections import (
        Faithfulness,
        AnswerRelevancy,
        ContextRecall,
        ContextPrecision,
    )

    print("\n📊 Running RAGAS evaluation (dùng LLM → tốn ~$0.01–0.05)...")

    # ── Chuẩn bị EvaluationDataset theo RAGAS 0.4.x format ──────────
    samples = [
        SingleTurnSample(
            user_input=r["question"],        # câu hỏi
            retrieved_contexts=r["contexts"],# list[str] – nội dung docs retrieved
            response=r["answer"],            # câu trả lời từ LLM
            reference=r["ground_truth"],     # câu trả lời kỳ vọng
        )
        for r in rag_outputs
    ]
    dataset = EvaluationDataset(samples=samples)

    # ── Khởi tạo evaluator ───────────────────────────────────────────
    ragas_llm, ragas_emb = setup_ragas_evaluator(api_key)

    # ── Chạy evaluation – metrics nhận llm/embeddings qua constructor ─
    # Faithfulness, ContextRecall, ContextPrecision → chỉ cần llm
    # AnswerRelevancy → cần cả llm + embeddings (tính cosine similarity)
    result = evaluate(
        dataset,
        metrics=[
            Faithfulness(llm=ragas_llm),
            AnswerRelevancy(llm=ragas_llm, embeddings=ragas_emb),
            ContextRecall(llm=ragas_llm),
            ContextPrecision(llm=ragas_llm),
        ],
        raise_exceptions=False,
    )

    return result


# ─────────────────────────── SAVE + PRINT ────────────────────────────────────

def interpret_score(score: float) -> str:
    """Diễn giải điểm số thành nhãn dễ hiểu."""
    if score >= 0.85:   return "🟢 Excellent"
    elif score >= 0.70: return "🟡 Good"
    elif score >= 0.55: return "🟠 Fair"
    else:               return "🔴 Poor"


def print_results(result, rag_outputs: List[Dict]):
    """In kết quả ra màn hình."""
    print("\n" + "=" * 65)
    print("📈 RAGAS EVALUATION RESULTS")
    print("=" * 65)

    metrics_map = {
        "faithfulness":       "Faithfulness        (câu trả lời trung thực với context?)",
        "answer_relevancy":   "Answer Relevancy    (câu trả lời đúng trọng tâm?)",
        "context_recall":     "Context Recall      (context có đủ thông tin không?)",
        "context_precision":  "Context Precision   (context retrieved có liên quan không?)",
    }

    scores = {}
    for key, label in metrics_map.items():
        val = result.get(key)
        if val is not None:
            score = float(val)
            scores[key] = score
            print(f"  {label}")
            print(f"    Score: {score:.4f}  {interpret_score(score)}")
        else:
            print(f"  {label}: N/A")

    if scores:
        avg = sum(scores.values()) / len(scores)
        print(f"\n  {'─'*50}")
        print(f"  Overall Average : {avg:.4f}  {interpret_score(avg)}")

    # Latency summary
    latencies = [r["latency_s"] for r in rag_outputs if r["latency_s"] >= 0]
    if latencies:
        print(f"\n  ⏱️  Avg latency  : {sum(latencies)/len(latencies):.2f}s")
        print(f"  ⏱️  Max latency  : {max(latencies):.2f}s")

    print("=" * 65)


def save_results(
    result,
    rag_outputs: List[Dict],
    output_path: str,
    mode_label: str,
):
    """Lưu kết quả chi tiết ra CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Per-question scores (nếu RAGAS cung cấp)
    rows = []
    for i, r in enumerate(rag_outputs):
        row = {
            "mode":          mode_label,
            "timestamp":     datetime.now().isoformat(),
            "question":      r["question"],
            "answer":        r["answer"][:300],
            "ground_truth":  r["ground_truth"],
            "n_contexts":    len(r["contexts"]),
            "used_k":        r["used_k"],
            "latency_s":     r["latency_s"],
            "context_preview": r["contexts"][0][:150] if r["contexts"] else "",
        }
        rows.append(row)

    # Aggregate scores
    agg_row = {
        "mode":         mode_label,
        "timestamp":    datetime.now().isoformat(),
        "question":     "=== AGGREGATE ===",
        "faithfulness":         result.get("faithfulness"),
        "answer_relevancy":     result.get("answer_relevancy"),
        "context_recall":       result.get("context_recall"),
        "context_precision":    result.get("context_precision"),
        "avg_latency_s":        sum(r["latency_s"] for r in rag_outputs if r["latency_s"] >= 0) / max(1, len(rows)),
    }

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        # Write aggregate first
        agg_writer = csv.DictWriter(f, fieldnames=list(agg_row.keys()))
        agg_writer.writeheader()
        agg_writer.writerow(agg_row)
        f.write("\n")

        # Write per-question
        q_writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        q_writer.writeheader()
        q_writer.writerows(rows)

    print(f"\n💾 Results saved → {output_path}")


# ─────────────────────────── MAIN ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG system với RAGAS metrics")
    parser.add_argument("--api-key",  type=str, default=os.getenv("OPENAI_API_KEY", ""),
                        help="OpenAI API key (hoặc set OPENAI_API_KEY env var)")
    parser.add_argument("--db",       type=str, default="faiss_news_db_ivf",
                        help="FAISS database directory")
    parser.add_argument("--no-hybrid", action="store_true",
                        help="Tắt hybrid search (dùng dense-only để so sánh)")
    parser.add_argument("--no-reranker", action="store_true",
                        help="Tắt reranker")
    parser.add_argument("--output",   type=str, default="",
                        help="Đường dẫn file CSV output (mặc định: results/eval_<mode>_<ts>.csv)")
    parser.add_argument("--questions", type=str, default="",
                        help="JSON file với custom test questions (list of {question, ground_truth})")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("❌ OpenAI API key required (--api-key or OPENAI_API_KEY env var)")
        sys.exit(1)

    # ── Mode label ──
    mode_parts = []
    if not args.no_hybrid:   mode_parts.append("hybrid")
    else:                    mode_parts.append("dense")
    if not args.no_reranker: mode_parts.append("rerank")
    mode_label = "+".join(mode_parts)

    # ── Output path ──
    if not args.output:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"results/eval_{mode_label}_{ts}.csv"

    # ── Load custom questions ──
    questions = TEST_QUESTIONS
    if args.questions and os.path.exists(args.questions):
        with open(args.questions, encoding="utf-8") as f:
            custom = json.load(f)
        questions = custom
        print(f"📋 Loaded {len(questions)} custom questions from {args.questions}")
    else:
        print(f"📋 Using {len(questions)} built-in test questions")

    # ── Initialize RAG ──
    print(f"\n🚀 Mode: [{mode_label}] | DB: {args.db}")
    from backend.rag_cli import RAGChatbot

    chatbot = RAGChatbot(
        db_dir=args.db,
        api_key=api_key,
        use_hybrid=not args.no_hybrid,
        use_reranker=not args.no_reranker,
    )

    # ── Collect RAG outputs ──
    print("\n⏳ Collecting RAG outputs for all test questions...")
    rag_outputs = collect_rag_outputs(chatbot, questions, verbose=True)

    # ── RAGAS Evaluation ──
    ragas_result = run_ragas_evaluation(rag_outputs, api_key)

    # ── Print & Save ──
    print_results(ragas_result, rag_outputs)
    save_results(ragas_result, rag_outputs, args.output, mode_label)

    print(f"\n✅ Evaluation complete! Mode: [{mode_label}]")
    print(
        "   Tip: Chạy lại với --no-hybrid để so sánh:\n"
        "   python evaluate_rag.py --api-key sk-... --no-hybrid"
    )


if __name__ == "__main__":
    main()

