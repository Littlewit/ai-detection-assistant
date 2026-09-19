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

// ==================== 样板拆分（多图支持） ====================
let splitImages = []; // {filename, originalName, dataUrl}

const uploadZone = document.getElementById("split-upload-zone");
const splitFileInput = document.getElementById("split-file");

uploadZone.addEventListener("click", () => splitFileInput.click());
uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("dragover"); });
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) handleMultiImageUpload(e.dataTransfer.files);
});
splitFileInput.addEventListener("change", () => {
    if (splitFileInput.files.length) handleMultiImageUpload(splitFileInput.files);
});

async function handleMultiImageUpload(files) {
    for (const file of files) {
        try {
            const formData = new FormData();
            formData.append("file", file);
            const res = await fetch(`${API_BASE}/api/split/upload`, { method: "POST", body: formData });
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();

            const dataUrl = await new Promise(resolve => {
                const reader = new FileReader();
                reader.onload = e => resolve(e.target.result);
                reader.readAsDataURL(file);
            });

            splitImages.push({
                filename: data.file_path,
                originalName: data.filename,
                dataUrl,
            });
        } catch (err) {
            alert(`上传 ${file.name} 失败: ${err.message}`);
        }
    }
    renderSplitGallery();
    splitFileInput.value = "";
}

function renderSplitGallery() {
    const gallery = document.getElementById("split-gallery");
    const btnGroup = document.getElementById("split-btn-group");
    if (splitImages.length === 0) {
        gallery.style.display = "none";
        btnGroup.style.display = "none";
        return;
    }
    gallery.style.display = "flex";
    btnGroup.style.display = "flex";
    gallery.innerHTML = splitImages.map((img, i) => `
        <div class="gallery-thumb" data-index="${i}">
            <img src="${img.dataUrl}" alt="${img.originalName}">
            <span class="gallery-name">${img.originalName}</span>
            <button class="gallery-remove" onclick="removeSplitImage(${i})" title="移除">×</button>
        </div>
    `).join("");
}

function removeSplitImage(index) {
    splitImages.splice(index, 1);
    renderSplitGallery();
}

function clearSplitImages() {
    splitImages = [];
    renderSplitGallery();
    document.getElementById("split-results").style.display = "none";
    document.getElementById("split-progress").style.display = "none";
}

async function analyzeAllSplit() {
    if (splitImages.length === 0) return;
    const btn = document.getElementById("btn-split");
    setLoading(btn, true);

    const progressEl = document.getElementById("split-progress");
    const resultsEl = document.getElementById("split-results");
    const tabsEl = document.getElementById("split-result-tabs");
    const panelsEl = document.getElementById("split-result-panels");

    progressEl.style.display = "block";
    resultsEl.style.display = "none";
    tabsEl.innerHTML = "";
    panelsEl.innerHTML = "";

    const allResults = [];

    for (let i = 0; i < splitImages.length; i++) {
        const img = splitImages[i];
        progressEl.innerHTML = `<div class="step-item step-active">
            <span class="step-num">${i + 1}/${splitImages.length}</span>
            <span class="step-name">${img.originalName}</span>
            <span class="step-status">⚙️ AI 分析中...</span>
        </div>`;
        // 将之前的标记为完成
        progressEl.querySelectorAll(".step-active:not(:last-child)").forEach(el => {
            el.classList.remove("step-active");
            el.classList.add("step-done");
            el.querySelector(".step-status").textContent = "✅ 完成";
        });

        try {
            const res = await fetch(`${API_BASE}/api/split/analyze/${img.filename}`, { method: "POST" });
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();
            allResults.push({ image: img, data });
        } catch (err) {
            allResults.push({ image: img, data: null, error: err.message });
        }
    }

    // 全部完成
    progressEl.querySelectorAll(".step-active").forEach(el => {
        el.classList.remove("step-active");
        el.classList.add("step-done");
        el.querySelector(".step-status").textContent = "✅ 完成";
    });

    // 渲染结果 Tabs
    renderSplitResults(allResults, tabsEl, panelsEl);
    resultsEl.style.display = "block";
    setLoading(btn, false);
}

function renderSplitResults(allResults, tabsEl, panelsEl) {
    // 生成 tab 按钮
    tabsEl.innerHTML = allResults.map((r, i) => {
        const name = r.image.originalName.length > 12
            ? r.image.originalName.substring(0, 10) + "..."
            : r.image.originalName;
        const active = i === 0 ? " active" : "";
        return `<button class="split-tab-btn${active}" onclick="switchSplitTab(${i})">${name}</button>`;
    }).join("");

    // 生成 panel
    panelsEl.innerHTML = allResults.map((r, i) => {
        const active = i === 0 ? " active" : "";
        if (r.error) {
            return `<div class="split-tab-panel${active}" data-panel="${i}">
                <div class="result-area"><span style="color:var(--danger)">分析失败: ${r.error}</span></div>
            </div>`;
        }
        const data = r.data;
        const analysis = data.analysis;

        let html = `<div class="split-tab-panel${active}" data-panel="${i}">`;
        html += `<div class="result-area">`;

        // 产品缩略图
        html += `<div class="split-result-header">
            <img src="${r.image.dataUrl}" class="split-result-thumb" alt="${r.image.originalName}">
            <div class="split-result-meta">
                <div class="product-info-header">
                    <span class="product-info-name">${analysis.product_name}</span>`;
        if (analysis.product_category) {
            html += `<span class="product-info-badge">${analysis.product_category}</span>`;
        }
        if (analysis.age_group) {
            html += `<span class="product-info-badge badge-age">适用${analysis.age_group}</span>`;
        }
        html += `</div>`;
        if (analysis.overall_structure) {
            html += `<p class="product-info-structure">${analysis.overall_structure}</p>`;
        }
        html += `</div></div>`;

        // 安全警示
        if (analysis.safety_warnings && analysis.safety_warnings.length > 0) {
            html += `<div class="split-safety-warnings">
                <div class="safety-warn-title">⚠️ 安全警示</div><ul>`;
            analysis.safety_warnings.forEach(w => { html += `<li>${w}</li>`; });
            html += `</ul></div>`;
        }

        // 组件表格
        html += `<h3>📋 组件拆分明细</h3>`;
        if (analysis.components && analysis.components.length > 0) {
            html += `<div class="split-table-wrapper"><table class="component-table">
                <tr><th>#</th><th>组件</th><th>材质</th><th>材质类别</th><th>颜色</th><th>数量</th><th>安全风险</th><th>检测项目</th><th>适用标准</th></tr>`;
            analysis.components.forEach((c, ci) => {
                const riskClass = c.is_small_part ? 'risk-high' : (c.safety_risk && c.safety_risk !== '无' ? 'risk-mid' : '');
                const riskText = c.is_small_part ? `⚠️ 小零件` : (c.safety_risk && c.safety_risk !== '无' ? c.safety_risk : '-');
                html += `<tr>
                    <td>${ci + 1}</td>
                    <td><strong>${c.name}</strong></td>
                    <td>${c.material}</td>
                    <td><span class="mat-badge">${c.material_category || ""}</span></td>
                    <td>${c.color || ""}</td>
                    <td>${c.quantity}</td>
                    <td class="${riskClass}">${riskText}</td>
                    <td>${(c.test_items || []).join("<br>")}</td>
                    <td>${(c.applicable_standards || []).join(", ")}</td>
                </tr>`;
            });
            html += `</table></div>`;
        }

        // 拆分示意图
        if (data.diagram_url) {
            html += `<div class="split-diagram-section">
                <h4>拆分示意图</h4>
                <img src="${data.diagram_url}" class="diagram-img" alt="拆分示意图">
            </div>`;
        }

        html += `</div></div>`;
        return html;
    }).join("");
}

function switchSplitTab(index) {
    document.querySelectorAll(".split-tab-btn").forEach((btn, i) => {
        btn.classList.toggle("active", i === index);
    });
    document.querySelectorAll(".split-tab-panel").forEach((panel, i) => {
        panel.classList.toggle("active", i === index);
    });
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
