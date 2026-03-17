(function () {
  const searchInput = document.getElementById("docSearch");
  const searchResults = document.getElementById("helpSearchResults");
  const searchPanel = searchInput?.closest(".search-panel") || null;
  const noteCards = Array.from(document.querySelectorAll(".note-card"));
  const filterButtons = Array.from(document.querySelectorAll("[data-note-filter]"));
  const checklistInputs = Array.from(document.querySelectorAll("[data-checklist-item]"));
  const searchEntries = Array.isArray(window.__HELP_SEARCH_INDEX__) ? window.__HELP_SEARCH_INDEX__ : [];
  const storageKey = "ur-print-fdm-help-checklist";
  const HIGHLIGHT_CLASS = "search-inline-highlight";
  let currentResults = [];
  let activeResultIndex = 0;

  function readChecklistState() {
    try {
      return JSON.parse(window.localStorage.getItem(storageKey) || "{}");
    } catch (error) {
      return {};
    }
  }

  function writeChecklistState(nextState) {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(nextState));
    } catch (error) {
      // Ignore storage failures in locked-down environments.
    }
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escapeRegExp(value) {
    return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function normalizeText(value) {
    return String(value || "").toLowerCase().trim();
  }

  function getSearchTokens(keyword) {
    return Array.from(new Set(normalizeText(keyword).split(/\s+/).filter(Boolean))).sort(
      (left, right) => right.length - left.length,
    );
  }

  function getPrimaryContentRoot() {
    return document.querySelector(".article-prose") || document.querySelector(".content") || document.body;
  }

  function setActiveNoteFilter(filterValue) {
    filterButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.noteFilter === filterValue);
    });
  }

  function applyNoteFilter() {
    const activeFilter = document.querySelector(".filter-chip.is-active")?.dataset.noteFilter || "all";
    noteCards.forEach((card) => {
      const matchesFilter = activeFilter === "all" || card.dataset.noteCategory === activeFilter;
      card.classList.toggle("is-hidden", !matchesFilter);
    });
  }

  function clearSearchHighlights(root) {
    if (!root) {
      return;
    }

    Array.from(root.querySelectorAll(`mark.${HIGHLIGHT_CLASS}`)).forEach((mark) => {
      const parent = mark.parentNode;
      if (!parent) {
        return;
      }
      parent.replaceChild(document.createTextNode(mark.textContent || ""), mark);
      parent.normalize();
    });
  }

  function highlightMatchesInText(value, keyword) {
    const text = String(value || "");
    const tokens = getSearchTokens(keyword);
    if (!tokens.length) {
      return escapeHtml(text);
    }

    const pattern = new RegExp(tokens.map(escapeRegExp).join("|"), "gi");
    let lastIndex = 0;
    let result = "";
    let match;

    while ((match = pattern.exec(text)) !== null) {
      result += escapeHtml(text.slice(lastIndex, match.index));
      result += `<mark class="${HIGHLIGHT_CLASS}">${escapeHtml(match[0])}</mark>`;
      lastIndex = match.index + match[0].length;
    }

    result += escapeHtml(text.slice(lastIndex));
    return result;
  }

  function highlightKeywordInContainer(container, keyword) {
    if (!container) {
      return;
    }

    clearSearchHighlights(container);
    const tokens = getSearchTokens(keyword);
    if (!tokens.length) {
      return;
    }

    const pattern = new RegExp(tokens.map(escapeRegExp).join("|"), "gi");
    const nodes = [];
    const walker = document.createTreeWalker(
      container,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode(node) {
          if (!node.nodeValue || !node.nodeValue.trim()) {
            return NodeFilter.FILTER_REJECT;
          }

          const parent = node.parentElement;
          if (!parent) {
            return NodeFilter.FILTER_REJECT;
          }

          if (
            ["SCRIPT", "STYLE", "MARK", "NOSCRIPT", "TEXTAREA", "INPUT"].includes(parent.tagName) ||
            parent.closest(".search-results")
          ) {
            return NodeFilter.FILTER_REJECT;
          }

          return NodeFilter.FILTER_ACCEPT;
        },
      },
    );

    while (walker.nextNode()) {
      nodes.push(walker.currentNode);
    }

    nodes.forEach((textNode) => {
      const text = textNode.nodeValue || "";
      pattern.lastIndex = 0;
      if (!pattern.test(text)) {
        return;
      }

      pattern.lastIndex = 0;
      let lastIndex = 0;
      let match;
      const fragment = document.createDocumentFragment();

      while ((match = pattern.exec(text)) !== null) {
        if (match.index > lastIndex) {
          fragment.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
        }

        const mark = document.createElement("mark");
        mark.className = HIGHLIGHT_CLASS;
        mark.textContent = match[0];
        fragment.appendChild(mark);
        lastIndex = match.index + match[0].length;
      }

      if (lastIndex < text.length) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
      }

      textNode.parentNode?.replaceChild(fragment, textNode);
    });
  }

  function flashTarget(target) {
    if (!target) {
      return;
    }

    target.classList.remove("search-hit");
    void target.offsetWidth;
    target.classList.add("search-hit");
    window.setTimeout(() => target.classList.remove("search-hit"), 1800);
  }

  function closeSearchResults() {
    currentResults = [];
    activeResultIndex = 0;
    if (!searchResults) {
      return;
    }
    searchResults.hidden = true;
    searchResults.innerHTML = "";
  }

  function scoreEntry(entry, keyword, tokens) {
    const title = normalizeText(entry.title);
    const excerpt = normalizeText(entry.excerpt);
    const kind = normalizeText(entry.kind);
    const keywords = normalizeText(entry.keywords);
    const haystack = `${title} ${excerpt} ${kind} ${keywords}`;

    if (!tokens.every((token) => haystack.includes(token))) {
      return -1;
    }

    let score = 0;
    if (title === keyword) {
      score += 180;
    }
    if (title.startsWith(keyword)) {
      score += 120;
    }
    if (title.includes(keyword)) {
      score += 90;
    }
    if (kind.includes(keyword)) {
      score += 40;
    }
    if (excerpt.includes(keyword)) {
      score += 28;
    }
    if (keywords.includes(keyword)) {
      score += 18;
    }

    tokens.forEach((token) => {
      if (title.startsWith(token)) {
        score += 22;
      }
      if (title.includes(token)) {
        score += 16;
      }
      if (excerpt.includes(token)) {
        score += 10;
      }
      if (keywords.includes(token)) {
        score += 6;
      }
    });

    return score;
  }

  function buildSearchResults(keyword) {
    const normalizedKeyword = normalizeText(keyword);
    if (!normalizedKeyword) {
      return [];
    }

    const tokens = getSearchTokens(keyword);
    return searchEntries
      .map((entry, index) => ({
        entry,
        score: scoreEntry(entry, normalizedKeyword, tokens),
        index,
      }))
      .filter((item) => item.score >= 0)
      .sort((left, right) => {
        if (right.score !== left.score) {
          return right.score - left.score;
        }
        return left.index - right.index;
      })
      .slice(0, 10)
      .map((item) => item.entry);
  }

  function renderSearchResults() {
    if (!searchResults) {
      return;
    }

    const keyword = searchInput?.value || "";
    const normalizedKeyword = normalizeText(keyword);
    clearSearchHighlights(getPrimaryContentRoot());

    if (!normalizedKeyword) {
      closeSearchResults();
      return;
    }

    currentResults = buildSearchResults(keyword);
    activeResultIndex = Math.min(activeResultIndex, Math.max(currentResults.length - 1, 0));
    searchResults.hidden = false;

    if (!currentResults.length) {
      searchResults.innerHTML = '<div class="search-empty">没有找到匹配内容，请换一个关键词试试。</div>';
      return;
    }

    searchResults.innerHTML = currentResults
      .map((entry, index) => {
        const isActive = index === activeResultIndex ? " is-active" : "";
        return (
          `<a class="search-result${isActive}" href="${escapeHtml(entry.href)}" data-result-index="${index}">` +
          `<div class="search-result__meta"><span class="badge badge--soft">${escapeHtml(entry.kind)}</span></div>` +
          `<strong class="search-result__title">${highlightMatchesInText(entry.title, keyword)}</strong>` +
          `<p class="search-result__excerpt">${highlightMatchesInText(entry.excerpt, keyword)}</p>` +
          "</a>"
        );
      })
      .join("");
  }

  function revealLocalTarget(href, keyword) {
    if (href.startsWith("#note-")) {
      setActiveNoteFilter("all");
      applyNoteFilter();
    }

    let target = null;
    try {
      target = document.querySelector(href);
    } catch (error) {
      target = null;
    }

    if (!target) {
      window.location.hash = href;
      return;
    }

    if (window.location.hash !== href) {
      try {
        window.history.replaceState(null, "", href);
      } catch (error) {
        window.location.hash = href;
      }
    }

    target.scrollIntoView({ behavior: "smooth", block: "start" });
    highlightKeywordInContainer(target, keyword);
    flashTarget(target);
  }

  function openSearchResult(result) {
    if (!result) {
      return;
    }

    const keyword = searchInput?.value.trim() || "";
    closeSearchResults();

    if (result.href.startsWith("#")) {
      revealLocalTarget(result.href, keyword);
      return;
    }

    const url = new URL(result.href, window.location.href);
    if (keyword) {
      url.searchParams.set("q", keyword);
    }
    window.location.href = url.toString();
  }

  function bindScrollSpy(selector, targetSelector, activeClass) {
    const links = Array.from(document.querySelectorAll(selector));
    const items = links
      .map((link) => {
        const href = link.getAttribute("href") || "";
        if (!href.startsWith("#")) {
          return null;
        }
        const target = document.getElementById(href.slice(1));
        if (!target || (targetSelector && !target.matches(targetSelector))) {
          return null;
        }
        return { link, target };
      })
      .filter(Boolean);

    if (!items.length) {
      return;
    }

    function updateActiveLink() {
      const threshold = window.innerHeight * 0.22;
      let current = items[0];

      items.forEach((item) => {
        if (item.target.getBoundingClientRect().top <= threshold) {
          current = item;
        }
      });

      items.forEach((item) => {
        item.link.classList.toggle(activeClass, item === current);
      });
    }

    updateActiveLink();
    window.addEventListener("scroll", updateActiveLink, { passive: true });
    window.addEventListener("resize", updateActiveLink);
    window.addEventListener("hashchange", updateActiveLink);
  }

  function applyInitialSearchHighlight() {
    const keyword = new URLSearchParams(window.location.search).get("q")?.trim() || "";
    if (!keyword) {
      return;
    }

    if (searchInput && !searchInput.value) {
      searchInput.value = keyword;
    }

    let target = null;
    if (window.location.hash) {
      try {
        target = document.querySelector(window.location.hash);
      } catch (error) {
        target = null;
      }
    }

    highlightKeywordInContainer(target || getPrimaryContentRoot(), keyword);
    if (target) {
      flashTarget(target);
    }
  }

  searchInput?.addEventListener("input", function () {
    activeResultIndex = 0;
    renderSearchResults();
  });

  searchInput?.addEventListener("focus", function () {
    if (searchInput.value.trim()) {
      renderSearchResults();
    }
  });

  searchInput?.addEventListener("keydown", function (event) {
    if (!currentResults.length) {
      if (event.key === "Escape") {
        searchInput.value = "";
        clearSearchHighlights(getPrimaryContentRoot());
        closeSearchResults();
      }
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeResultIndex = (activeResultIndex + 1) % currentResults.length;
      renderSearchResults();
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      activeResultIndex = (activeResultIndex - 1 + currentResults.length) % currentResults.length;
      renderSearchResults();
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      openSearchResult(currentResults[activeResultIndex] || currentResults[0]);
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      searchInput.value = "";
      clearSearchHighlights(getPrimaryContentRoot());
      closeSearchResults();
    }
  });

  searchResults?.addEventListener("click", function (event) {
    const item = event.target.closest(".search-result");
    if (!item) {
      return;
    }
    event.preventDefault();
    const index = Number(item.dataset.resultIndex || 0);
    openSearchResult(currentResults[index]);
  });

  document.addEventListener("click", function (event) {
    if (!searchPanel || searchResults?.hidden) {
      return;
    }
    if (searchPanel.contains(event.target)) {
      return;
    }
    closeSearchResults();
  });

  filterButtons.forEach((button) => {
    button.addEventListener("click", function () {
      setActiveNoteFilter(button.dataset.noteFilter || "all");
      applyNoteFilter();
    });
  });

  const checklistState = readChecklistState();
  checklistInputs.forEach((input) => {
    const key = input.dataset.checklistItem;
    if (!key) {
      return;
    }
    input.checked = Boolean(checklistState[key]);
    input.addEventListener("change", function () {
      checklistState[key] = input.checked;
      writeChecklistState(checklistState);
    });
  });

  bindScrollSpy(".sidebar__nav a[href^='#']", ".doc-section", "is-current");
  bindScrollSpy(".article-toc a[href^='#']", "h2, h3", "is-current");
  applyNoteFilter();
  applyInitialSearchHighlight();
})();
