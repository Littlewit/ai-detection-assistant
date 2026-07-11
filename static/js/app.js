/**
 * AI检测助手 - 前端交互逻辑
 */

const API_BASE = "";

// ==================== Tab 切换 ====================
document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
});

// ==================== 智能问答 ====================
async function askQuestion() {
    const question = document.getElementById("qa-question").value.trim();
    const category = document.getElementById("qa-category").value;
    if (!question) { alert("请输入提问内容"); return; }

    const btn = document.getElementById("btn-qa");
    setLoading(btn, true);

    const answerEl = document.getElementById("qa-answer");
    const resultArea = document.getElementById("qa-result");
    const sourcesArea = document.getElementById("qa-sources");

    answerEl.innerHTML = "";
    resultArea.style.display = "block";
    sourcesArea.style.display = "none";

    let fullText = "";

    try {
        const res = await fetch(`${API_BASE}/api/qa/ask/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, category: category === "all" ? null : category }),
        });
        if (!res.ok) throw new Error(await res.text());

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop(); // 保留未完成的行

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const payload = line.slice(6).trim();
                if (payload === "[DONE]") break;

                try {
                    const evt = JSON.parse(payload);
                    if (evt.type === "sources" && evt.sources && evt.sources.length > 0) {
                        document.getElementById("qa-sources-list").textContent = evt.sources.join(", ");
                        sourcesArea.style.display = "block";
                    } else if (evt.type === "token") {
                        fullText += evt.content;
                        answerEl.innerHTML = marked.parse(fullText);
                    }
                } catch (_) { /* 忽略解析错误 */ }
            }
        }

        // 最终渲染
        answerEl.innerHTML = marked.parse(fullText);
    } catch (err) {
        answerEl.innerHTML = `<span style="color:var(--danger)">问答出错: ${err.message}</span>`;
    } finally {
        setLoading(btn, false);
    }
}

// ==================== 样板拆分 ====================
let uploadedImageFilename = null;

// 上传区域交互
const uploadZone = document.getElementById("split-upload-zone");
const splitFileInput = document.getElementById("split-file");

uploadZone.addEventListener("click", () => splitFileInput.click());
uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("dragover"); });
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
        splitFileInput.files = e.dataTransfer.files;
        handleImageUpload(e.dataTransfer.files[0]);
    }
});
splitFileInput.addEventListener("change", () => {
    if (splitFileInput.files.length) handleImageUpload(splitFileInput.files[0]);
});

async function handleImageUpload(file) {
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_BASE}/api/split/upload`, { method: "POST", body: formData });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        uploadedImageFilename = data.file_path;

        // 显示预览
        const reader = new FileReader();
        reader.onload = e => {
            document.getElementById("split-preview-img").src = e.target.result;
            document.getElementById("split-preview").style.display = "block";
        };
        reader.readAsDataURL(file);
        document.getElementById("split-filename").textContent = `已上传: ${data.filename}`;
        document.getElementById("btn-split").disabled = false;
        document.getElementById("split-result").style.display = "none";
    } catch (err) {
        alert("上传失败: " + err.message);
    }
}

async function analyzeSplit() {
    if (!uploadedImageFilename) return;
    const btn = document.getElementById("btn-split");
    setLoading(btn, true);

    try {
        const res = await fetch(`${API_BASE}/api/split/analyze/${uploadedImageFilename}`, { method: "POST" });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        // 渲染拆分结果表格
        const analysis = data.analysis;
        let html = `<p><strong>产品名称：</strong>${analysis.product_name}</p>`;
        html += `<p><strong>整体结构：</strong>${analysis.overall_structure}</p>`;

        if (analysis.components && analysis.components.length > 0) {
            html += `<table class="component-table">
                <tr><th>#</th><th>组件</th><th>材质</th><th>类别</th><th>数量</th><th>检测项目</th><th>适用标准</th></tr>`;
            analysis.components.forEach((c, i) => {
                html += `<tr>
                    <td>${i + 1}</td>
                    <td>${c.name}</td>
                    <td>${c.material}</td>
                    <td>${c.material_category || ""}</td>
                    <td>${c.quantity}</td>
                    <td>${(c.test_items || []).join(", ")}</td>
                    <td>${(c.applicable_standards || []).join(", ")}</td>
                </tr>`;
            });
            html += `</table>`;
        }

        document.getElementById("split-analysis").innerHTML = html;

        if (data.diagram_url) {
            document.getElementById("split-diagram").src = data.diagram_url;
            document.getElementById("split-diagram-container").style.display = "block";
        } else {
            document.getElementById("split-diagram-container").style.display = "none";
        }

        document.getElementById("split-result").style.display = "block";
    } catch (err) {
        alert("分析失败: " + err.message);
    } finally {
        setLoading(btn, false);
    }
}

// ==================== 报告审核 ====================
const reviewFiles = { app: null, split: null, report: null };

["app", "split", "report"].forEach(type => {
    const input = document.getElementById(`review-${type}`);
    input.addEventListener("change", async () => {
        if (!input.files.length) return;
        const file = input.files[0];
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch(`${API_BASE}/api/review/upload?file_type=${type}`, {
                method: "POST", body: formData,
            });
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();
            reviewFiles[type] = data.file_path;
            document.getElementById(`review-${type}-name`).textContent = `✓ ${data.filename}`;
            document.getElementById(`review-${type}-name`).style.color = "var(--success)";
        } catch (err) {
            alert(`上传${type}失败: ${err.message}`);
            return;
        }
        checkReviewReady();
    });
});

function checkReviewReady() {
    const ready = reviewFiles.app && reviewFiles.split && reviewFiles.report;
    document.getElementById("btn-review").disabled = !ready;
}

async function reviewReport() {
    const btn = document.getElementById("btn-review");
    setLoading(btn, true);

    const resultArea = document.getElementById("review-result");
    const progressEl = document.getElementById("review-progress");
    const conclusionEl = document.getElementById("review-conclusion");
    const totalEl = document.getElementById("review-total");
    const reportEl = document.getElementById("review-report-content");

    resultArea.style.display = "block";
    progressEl.innerHTML = "";
    conclusionEl.style.display = "none";
    totalEl.style.display = "none";
    reportEl.style.display = "none";
    reportEl.innerHTML = "";

    let fullText = "";

    try {
        const params = new URLSearchParams({
            application_filename: reviewFiles.app,
            split_table_filename: reviewFiles.split,
            report_filename: reviewFiles.report,
        });
        const res = await fetch(`${API_BASE}/api/review/review/stream?${params}`, { method: "POST" });
        if (!res.ok) throw new Error(await res.text());

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const payload = line.slice(6).trim();
                if (payload === "[DONE]") break;

                try {
                    const evt = JSON.parse(payload);

                    if (evt.type === "step") {
                        // 显示审核步骤进度
                        const stepHtml = `<div class="step-item step-active">
                            <span class="step-num">${evt.step}/${evt.total}</span>
                            <span class="step-name">${evt.name}</span>
                            <span class="step-status">⚙️ 进行中...</span>
                        </div>`;
                        // 将上一步标记为完成
                        progressEl.querySelectorAll(".step-active").forEach(el => {
                            el.classList.remove("step-active");
                            el.classList.add("step-done");
                            el.querySelector(".step-status").textContent = "✅ 完成";
                        });
                        progressEl.innerHTML += stepHtml;
                    } else if (evt.type === "meta") {
                        // 审核结果元数据
                        progressEl.querySelectorAll(".step-active").forEach(el => {
                            el.classList.remove("step-active");
                            el.classList.add("step-done");
                            el.querySelector(".step-status").textContent = "✅ 完成";
                        });

                        conclusionEl.textContent = `审核结论: ${evt.conclusion}`;
                        conclusionEl.className = "conclusion-badge";
                        if (evt.conclusion === "通过") conclusionEl.classList.add("conclusion-pass");
                        else if (evt.conclusion === "需修改") conclusionEl.classList.add("conclusion-modify");
                        else conclusionEl.classList.add("conclusion-reject");
                        conclusionEl.style.display = "inline-block";

                        totalEl.textContent = `共发现 ${evt.total_issues} 个问题`;
                        totalEl.style.display = "inline";

                        reportEl.style.display = "block";
                    } else if (evt.type === "token") {
                        fullText += evt.content;
                        reportEl.innerHTML = marked.parse(fullText);
                    }
                } catch (_) { /* 忽略解析错误 */ }
            }
        }

        // 最终渲染
        if (fullText) {
            reportEl.style.display = "block";
            reportEl.innerHTML = marked.parse(fullText);
        }
    } catch (err) {
        progressEl.innerHTML = `<span style="color:var(--danger)">审核失败: ${err.message}</span>`;
    } finally {
        setLoading(btn, false);
    }
}

// ==================== 工具函数 ====================
function setLoading(btn, loading) {
    const text = btn.querySelector(".btn-text");
    const load = btn.querySelector(".btn-loading");
    if (loading) {
        text.style.display = "none";
        load.style.display = "inline";
        btn.disabled = true;
    } else {
        text.style.display = "inline";
        load.style.display = "none";
        btn.disabled = false;
    }
}
