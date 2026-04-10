const menuButton = document.getElementById("menu-button");
const mobileMenu = document.getElementById("mobile-menu");
const navLinks = document.querySelectorAll('a[href^="#"]');
const testimonialsList = document.getElementById("testimonials-list");
const enrollmentForm = document.getElementById("enrollment-form");
const formStatus = document.getElementById("form-status");
const submitButton = document.getElementById("submit-button");
const liveDataSummary = document.getElementById("live-data-summary");
const serverStatus = document.getElementById("server-status");
const statElements = document.querySelectorAll("[data-stat]");

const observer = typeof IntersectionObserver !== "undefined"
  ? new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.15,
      }
    )
  : null;

function observeAnimatedItems(scope = document) {
  if (!observer) {
    return;
  }

  scope.querySelectorAll("[data-animate]").forEach((item) => observer.observe(item));
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char] || char;
  });
}

function formatStatValue(key, value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue) || numericValue < 0) {
    return key === "mentors" ? "25+" : "0";
  }

  if (key === "mentors") {
    return `${numericValue}+`;
  }

  return numericValue.toLocaleString("id-ID");
}

function updateStats(stats = {}) {
  statElements.forEach((element) => {
    const key = element.dataset.stat;
    if (!key || !(key in stats)) {
      return;
    }

    element.textContent = formatStatValue(key, stats[key]);
  });

  if (liveDataSummary) {
    const testimonials = Number(stats.testimonials ?? 0);
    const enrollments = Number(stats.enrollments ?? 0);
    liveDataSummary.textContent = `${enrollments} pendaftaran, ${testimonials} testimoni`;
  }
}

function updateServerStatus(state, message) {
  if (!serverStatus) {
    return;
  }

  const colors = {
    loading: "bg-amber-400",
    online: "bg-forest-500",
    offline: "bg-rose-500",
  };

  serverStatus.innerHTML = `
    <span class="h-2.5 w-2.5 rounded-full ${colors[state] || colors.loading}"></span>
    ${escapeHtml(message)}
  `;
}

function renderTestimonials(testimonials) {
  if (!testimonialsList) {
    return;
  }

  if (!Array.isArray(testimonials) || testimonials.length === 0) {
    testimonialsList.innerHTML = `
      <div class="rounded-[1.8rem] border border-slate-200 bg-white p-7 shadow-sm" data-animate>
        <p class="text-sm font-semibold text-slate-500">Belum ada testimoni.</p>
        <p class="mt-4 text-slate-600">Database aktif, tetapi datanya masih kosong.</p>
      </div>
    `;
    observeAnimatedItems(testimonialsList);
    return;
  }

  testimonialsList.innerHTML = testimonials
    .map((item) => {
      const stars = "&#9733;".repeat(Math.max(1, Math.min(Number(item.rating) || 5, 5)));
      return `
        <figure class="rounded-[1.8rem] border border-slate-200 bg-white p-7 shadow-sm" data-animate>
          <div class="flex items-center gap-1 text-amber-500">
            <span>${stars}</span>
          </div>
          <blockquote class="mt-5 text-lg leading-8 text-slate-700">
            "${escapeHtml(item.quote)}"
          </blockquote>
          <figcaption class="mt-6">
            <p class="font-display text-lg font-extrabold text-slate-900">${escapeHtml(item.name)}</p>
            <p class="text-sm text-slate-500">${escapeHtml(item.role)}</p>
          </figcaption>
        </figure>
      `;
    })
    .join("");

  observeAnimatedItems(testimonialsList);
}

async function checkServerHealth() {
  updateServerStatus("loading", "Memeriksa status server...");

  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      throw new Error("Server tidak merespons");
    }

    updateServerStatus("online", "Server aktif dan siap menerima pendaftaran");
  } catch (error) {
    updateServerStatus("offline", "Server belum aktif, jalankan python server.py");
  }
}

async function loadSiteStats() {
  try {
    const response = await fetch("/api/site-stats");
    if (!response.ok) {
      throw new Error("Gagal memuat statistik");
    }

    const payload = await response.json();
    updateStats(payload.stats || {});
  } catch (error) {
    if (liveDataSummary) {
      liveDataSummary.textContent = "Statistik live belum tersedia";
    }
  }
}

async function loadTestimonials() {
  if (!testimonialsList) {
    return;
  }

  try {
    const response = await fetch("/api/testimonials");
    if (!response.ok) {
      throw new Error("Gagal mengambil testimoni");
    }

    const payload = await response.json();
    renderTestimonials(payload.testimonials);
    updateServerStatus("online", "Testimoni berhasil dimuat dari database");
  } catch (error) {
    testimonialsList.innerHTML = `
      <div class="rounded-[1.8rem] border border-rose-200 bg-white p-7 shadow-sm" data-animate>
        <p class="text-sm font-semibold text-rose-600">Database belum terhubung.</p>
        <p class="mt-4 text-slate-600">Buka halaman lewat <code>python server.py</code> agar testimoni dimuat dari SQLite.</p>
      </div>
    `;
    observeAnimatedItems(testimonialsList);
    updateServerStatus("offline", "Database belum terhubung");
  }
}

async function handleEnrollmentSubmit(event) {
  event.preventDefault();

  if (!enrollmentForm || !formStatus || !submitButton) {
    return;
  }

  const formData = new FormData(enrollmentForm);
  const payload = {
    fullName: formData.get("fullName")?.toString().trim(),
    email: formData.get("email")?.toString().trim(),
    phone: formData.get("phone")?.toString().trim(),
    instrument: formData.get("instrument")?.toString().trim(),
    learningMode: formData.get("learningMode")?.toString().trim(),
    message: formData.get("message")?.toString().trim(),
    website: formData.get("website")?.toString().trim(),
  };

  formStatus.textContent = "Mengirim data pendaftaran...";
  formStatus.className = "mt-4 text-sm font-semibold text-forest-700";
  submitButton.disabled = true;
  submitButton.textContent = "Mengirim...";
  submitButton.classList.add("cursor-not-allowed", "opacity-70");

  try {
    const response = await fetch("/api/enrollments", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Pendaftaran gagal disimpan");
    }

    enrollmentForm.reset();
    formStatus.textContent = result.message || "Pendaftaran berhasil disimpan.";
    formStatus.className = "mt-4 text-sm font-semibold text-forest-700";
    await loadSiteStats();
  } catch (error) {
    formStatus.textContent = error.message || "Terjadi kesalahan saat mengirim form.";
    formStatus.className = "mt-4 text-sm font-semibold text-rose-600";
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Kirim Pendaftaran";
    submitButton.classList.remove("cursor-not-allowed", "opacity-70");
  }
}

if (menuButton && mobileMenu) {
  menuButton.addEventListener("click", () => {
    const isExpanded = menuButton.getAttribute("aria-expanded") === "true";
    menuButton.setAttribute("aria-expanded", String(!isExpanded));
    mobileMenu.classList.toggle("hidden");
  });
}

navLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    const targetId = link.getAttribute("href");
    if (!targetId || !targetId.startsWith("#")) {
      return;
    }

    const target = document.querySelector(targetId);
    if (!target) {
      return;
    }

    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });

    if (mobileMenu && menuButton && !mobileMenu.classList.contains("hidden")) {
      mobileMenu.classList.add("hidden");
      menuButton.setAttribute("aria-expanded", "false");
    }
  });
});

if (enrollmentForm) {
  enrollmentForm.addEventListener("submit", handleEnrollmentSubmit);
}

observeAnimatedItems();
checkServerHealth();
loadSiteStats();
loadTestimonials();
