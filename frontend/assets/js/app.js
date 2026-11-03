const API = "/api";

const LeadHunter = {
  async fetchJSON(url, options = {}) {
    const resp = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(text || resp.statusText);
    }
    if (resp.status === 204) return null;
    const ct = resp.headers.get("content-type") || "";
    if (ct.includes("application/json")) return resp.json();
    return resp.text();
  },

  statusBadge(status) {
    return `<span class="badge text-bg-secondary">${status}</span>`;
  },

  async loadDashboard() {
    const data = await this.fetchJSON(`${API}/dashboard`);
    const cards = [
      ["Компаний", data.total_companies, ""],
      ["Проанализировано", data.analyzed_leads, ""],
      ["Горячие", data.hot_leads, "hot"],
      ["Тёплые", data.warm_leads, "warm"],
      ["Задач поиска", data.search_tasks, ""],
    ];
    document.getElementById("stats-cards").innerHTML = cards
      .map(
        ([title, value, cls]) => `
      <div class="col-md-4 col-lg">
        <div class="card stat-card ${cls} shadow-sm"><div class="card-body">
          <div class="text-muted small">${title}</div>
          <div class="fs-3 fw-semibold">${value}</div>
        </div></div>
      </div>`
      )
      .join("");

    const recent = document.getElementById("recent-companies");
    recent.innerHTML =
      data.recent_companies
        .map(
          (c) => `<li class="list-group-item d-flex justify-content-between">
        <span>${c.name}</span><small class="text-muted">${c.region || ""}</small>
      </li>`
        )
        .join("") || '<li class="list-group-item text-muted">Пока пусто</li>';

    const dist = data.temperature_distribution || {};
    document.getElementById("temperature-chart").innerHTML = Object.entries(dist)
      .map(([k, v]) => `<div class="d-flex justify-content-between border-bottom py-1"><span>${k}</span><strong>${v}</strong></div>`)
      .join("");
  },

  initSearchForm() {
    const form = document.getElementById("search-form");
    const statusBox = document.getElementById("search-status");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const payload = Object.fromEntries(fd.entries());
      payload.limit = Number(payload.limit);
      statusBox.classList.remove("d-none", "alert-danger");
      statusBox.classList.add("alert-info");
      statusBox.textContent = "Задача создана, ожидание обработки...";
      try {
        const task = await this.fetchJSON(`${API}/search`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
        await this.pollSearch(task.id, statusBox);
      } catch (err) {
        statusBox.classList.replace("alert-info", "alert-danger");
        statusBox.textContent = err.message;
      }
    });
  },

  async pollSearch(taskId, statusBox) {
    for (let i = 0; i < 120; i++) {
      const task = await this.fetchJSON(`${API}/search/${taskId}`);
      statusBox.textContent = `Статус: ${task.status}. Найдено: ${task.total_found}, обработано: ${task.total_processed}`;
      if (task.status === "completed" || task.status === "failed") {
        if (task.status === "completed") {
          statusBox.classList.replace("alert-info", "alert-success");
          statusBox.innerHTML += ` <a href="/leads.html">Перейти к лидам</a>`;
        } else {
          statusBox.classList.replace("alert-info", "alert-danger");
          statusBox.textContent += `. Ошибка: ${task.error_message || "unknown"}`;
        }
        return;
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
  },

  async loadLeadsTable() {
    const params = new URLSearchParams();
    const q = document.getElementById("filter-q").value.trim();
    const status = document.getElementById("filter-status").value;
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    document.getElementById("filter-apply").onclick = () => this.loadLeadsTable();

    const leads = await this.fetchJSON(`${API}/leads?${params.toString()}`);
    const tbody = document.getElementById("leads-table");
    tbody.innerHTML = leads
      .map(
        (l) => `<tr style="cursor:pointer" onclick="location.href='/lead.html?id=${l.id}'">
        <td>${l.company_name}</td>
        <td>${l.industry || "—"}</td>
        <td>${l.primary_need || "—"}</td>
        <td>${l.score ?? "—"}</td>
        <td>${LeadHunter.statusBadge(l.status)}</td>
      </tr>`
      )
      .join("");
  },

  async loadLeadDetail() {
    const id = new URLSearchParams(location.search).get("id");
    if (!id) return;
    const lead = await this.fetchJSON(`${API}/leads/${id}`);
    const root = document.getElementById("lead-detail");
    root.innerHTML = `
      <div class="d-flex justify-content-between align-items-start mb-3">
        <div>
          <h1 class="h3">${lead.company.name}</h1>
          <p class="text-muted mb-0">${lead.company.website || ""}</p>
        </div>
        <div class="text-end">
          <div class="display-6">${lead.score ?? "—"}</div>
          <div>${lead.temperature || ""} · ${lead.status}</div>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-lg-6">
          <div class="card shadow-sm mb-3"><div class="card-header">Контакты</div><div class="card-body">
            <div>Телефон: ${lead.company.phone || "—"}</div>
            <div>Email: ${lead.company.email || "—"}</div>
            <div>Регион: ${lead.company.region || "—"}</div>
          </div></div>
          <div class="card shadow-sm mb-3"><div class="card-header">AI-анализ</div><div class="card-body pre-wrap">${JSON.stringify(lead.ai_analysis, null, 2) || "—"}</div></div>
        </div>
        <div class="col-lg-6">
          <div class="card shadow-sm mb-3"><div class="card-header">Оценка</div><div class="card-body pre-wrap">${lead.score_explanation || "—"}</div></div>
          <div class="card shadow-sm mb-3"><div class="card-header">Действия</div><div class="card-body d-flex flex-wrap gap-2">
            <select id="lead-status" class="form-select w-auto">
              ${["new","analyzed","qualified","in_progress","contacted","rejected","client"].map(s=>`<option value="${s}" ${s===lead.status?"selected":""}>${s}</option>`).join("")}
            </select>
            <button class="btn btn-outline-primary" id="btn-save-status">Сохранить статус</button>
            <button class="btn btn-outline-secondary" id="btn-analyze">Повторный анализ</button>
            <button class="btn btn-primary" id="btn-offer">Сгенерировать предложение</button>
          </div></div>
          <div class="card shadow-sm mb-3"><div class="card-header">Предложения</div><div class="card-body pre-wrap" id="offers-block">${(lead.offers||[]).map(o=>o.content).join("\n\n---\n\n") || "Пока нет"}</div></div>
        </div>
      </div>`;

    document.getElementById("btn-save-status").onclick = async () => {
      const status = document.getElementById("lead-status").value;
      await this.fetchJSON(`${API}/leads/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      location.reload();
    };
    document.getElementById("btn-analyze").onclick = async () => {
      await this.fetchJSON(`${API}/leads/${id}/analyze`, { method: "POST" });
      location.reload();
    };
    document.getElementById("btn-offer").onclick = async () => {
      const offer = await this.fetchJSON(`${API}/leads/${id}/offer`, { method: "POST" });
      document.getElementById("offers-block").textContent = offer.content;
    };
  },
};

window.LeadHunter = LeadHunter;
