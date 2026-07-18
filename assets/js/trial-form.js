(function () {
  "use strict";

  var markerKey = "salaamTrialSubmissionConfirmed";
  var markerLifetimeMs = 5 * 60 * 1000;

  function validEndpoint(value) {
    try {
      var url = new URL(value);
      return url.protocol === "https:"
        && url.hostname === "formspree.io"
        && /^\/f\/[A-Za-z0-9_-]{5,}$/.test(url.pathname)
        && !url.search
        && !url.hash
        && value.indexOf("@") === -1
        && value.indexOf("FORM_ID") === -1;
    } catch (error) {
      return false;
    }
  }

  function consumeSuccessMarker() {
    var confirmed = document.querySelector("[data-success-state='confirmed']");
    var direct = document.querySelector("[data-success-state='direct']");
    if (!confirmed || !direct) return;
    var marker = null;
    try {
      marker = JSON.parse(sessionStorage.getItem(markerKey) || "null");
      sessionStorage.removeItem(markerKey);
    } catch (error) {
      marker = null;
    }
    if (!marker || marker.confirmed !== true || !Number.isFinite(marker.at)
        || Date.now() - marker.at < 0 || Date.now() - marker.at > markerLifetimeMs) return;
    direct.hidden = true;
    confirmed.hidden = false;
    var heading = confirmed.querySelector("h1");
    if (heading) heading.focus();
  }

  function appendDescription(field, errorId) {
    var ids = (field.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
    if (ids.indexOf(errorId) === -1) ids.push(errorId);
    field.setAttribute("aria-describedby", ids.join(" "));
  }

  function showFieldError(form, name, message) {
    var field = form.elements.namedItem(name);
    var error = document.getElementById(name + "-error");
    if (!field || !error) return;
    var target = field.length && !field.tagName ? field[0] : field;
    target.setAttribute("aria-invalid", "true");
    appendDescription(target, error.id);
    error.textContent = message;
    error.hidden = false;
  }

  function clearErrors(form, summary) {
    summary.hidden = true;
    summary.textContent = "";
    form.querySelectorAll("[aria-invalid='true']").forEach(function (field) {
      field.removeAttribute("aria-invalid");
    });
    form.querySelectorAll(".field-error").forEach(function (error) {
      error.hidden = true;
      error.textContent = "";
    });
  }

  function showSummary(summary, messages) {
    summary.textContent = "Please review: " + messages.join(" ");
    summary.hidden = false;
    summary.focus();
  }

  function customValidation(form) {
    var role = form.elements.namedItem("contact_role").value;
    var group = form.elements.namedItem("learner_group").value;
    var program = form.elements.namedItem("program").value;
    var errors = [];
    if (role === "adult_woman" && group !== "adult_woman") {
      errors.push(["learner_group", "An adult woman learner must select Adult woman as the learner group."]);
    }
    if (role === "parent_guardian" && group === "adult_woman") {
      errors.push(["learner_group", "Select a child age group, or choose Adult woman learner as the contact role."]);
    }
    if (group === "adult_woman" && program === "culture_ethics") {
      errors.push(["program", "Afghan Culture & Islamic Ethics is currently planned for learners aged 5–16."]);
    }
    return errors;
  }

  function initialiseForm(form) {
    var endpoint = form.dataset.endpoint || "";
    var verified = form.dataset.endpointVerified === "true";
    if (!verified || !validEndpoint(endpoint)) return;

    var button = form.querySelector("[type='submit']");
    var summary = document.getElementById("error-summary");
    var submitting = false;

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      if (submitting) return;
      clearErrors(form, summary);

      var messages = [];
      if (!form.checkValidity()) {
        var invalidNames = new Set();
        form.querySelectorAll(":invalid").forEach(function (field) {
          if (!field.name || invalidNames.has(field.name)) return;
          invalidNames.add(field.name);
          var message = field.validationMessage || "Complete this required field.";
          showFieldError(form, field.name, message);
          messages.push(message);
        });
      }
      customValidation(form).forEach(function (item) {
        showFieldError(form, item[0], item[1]);
        messages.push(item[1]);
      });
      if (messages.length) {
        showSummary(summary, messages);
        return;
      }

      submitting = true;
      button.disabled = true;
      button.textContent = "Submitting securely…";
      form.setAttribute("aria-busy", "true");
      try {
        var response = await fetch(endpoint, {
          method: "POST",
          body: new FormData(form),
          headers: { "Accept": "application/json" }
        });
        var payload = await response.json().catch(function () { return null; });
        if (!response.ok || !payload || payload.ok !== true) {
          var providerErrors = payload && Array.isArray(payload.errors) ? payload.errors : [];
          providerErrors.forEach(function (item) {
            if (item && item.field && form.elements.namedItem(item.field)) {
              showFieldError(form, item.field, String(item.message || "Check this field."));
            }
          });
          throw new Error(providerErrors.map(function (item) { return String(item.message || ""); }).filter(Boolean).join(" ") || "The secure form provider could not confirm the submission.");
        }
        try {
          sessionStorage.setItem(markerKey, JSON.stringify({ confirmed: true, at: Date.now() }));
        } catch (storageError) {
          showSummary(summary, ["Your request was accepted, but this browser could not open the confirmation page. Please do not submit it again."]);
          button.textContent = "Request received";
          form.removeAttribute("aria-busy");
          return;
        }
        window.location.assign("/success/");
      } catch (error) {
        showSummary(summary, [error.message || "The request could not be sent. Check your connection and try again."]);
        submitting = false;
        button.disabled = false;
        button.textContent = "Request a Free Trial";
        form.removeAttribute("aria-busy");
      }
    });
  }

  consumeSuccessMarker();
  var form = document.querySelector("[data-trial-form]");
  if (form) initialiseForm(form);
}());
