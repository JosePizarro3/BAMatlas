function setupExpertiseAutocomplete(input) {
  const endpoint = input.dataset.autocompleteUrl;
  if (!endpoint) {
    return;
  }

  const mode = input.dataset.expertiseSuggestions || "single";
  const container = document.createElement("div");
  container.className = "autocomplete-results";
  container.hidden = true;
  input.parentElement.appendChild(container);

  let requestCounter = 0;

  function getQuery() {
    if (mode === "multi") {
      const parts = input.value.split(",");
      return parts.at(-1).trim();
    }
    return input.value.trim();
  }

  function replaceValue(value) {
    if (mode === "multi") {
      const parts = input.value
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean);
      parts[parts.length - 1] = value;
      input.value = `${parts.join(", ")}${parts.length ? ", " : ""}`;
      return;
    }
    input.value = value;
  }

  async function updateSuggestions() {
    const query = getQuery();
    if (query.length < 2) {
      container.hidden = true;
      container.replaceChildren();
      return;
    }

    const currentRequest = ++requestCounter;
    const response = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`);
    if (!response.ok || currentRequest !== requestCounter) {
      return;
    }

    const payload = await response.json();
    container.replaceChildren();

    if (!payload.results.length) {
      container.hidden = true;
      return;
    }

    payload.results.forEach((result) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "autocomplete-option";
      button.textContent = result;
      button.addEventListener("click", () => {
        replaceValue(result);
        container.hidden = true;
        container.replaceChildren();
        input.focus();
      });
      container.appendChild(button);
    });

    container.hidden = false;
  }

  input.addEventListener("input", () => {
    window.clearTimeout(input.autocompleteTimer);
    input.autocompleteTimer = window.setTimeout(updateSuggestions, 120);
  });

  input.addEventListener("blur", () => {
    window.setTimeout(() => {
      container.hidden = true;
    }, 150);
  });
}

document.querySelectorAll("[data-expertise-suggestions]").forEach(setupExpertiseAutocomplete);
