(function () {
  "use strict";

  var whatsappBaseUrl = "https://wa.me/34614401172?text=";
  var buttonLabel = "Continue in WhatsApp";
  var fieldLimits = {
    contact_name: 80,
    country_timezone: 100,
    preferred_schedule: 400,
    learning_goal: 500
  };
  var labels = {
    contact_role: {
      parent_guardian: "Parent or guardian",
      adult_woman: "Adult woman learner"
    },
    learner_age_group: {
      age_5_7: "Age 5–7",
      age_8_11: "Age 8–11",
      age_12_16: "Age 12–16",
      adult_woman: "Adult woman"
    },
    program: {
      quran: "Quran",
      dari_persian: "Dari/Persian",
      culture_ethics: "Afghan Culture & Islamic Ethics"
    },
    frequency: {
      "1_week": "1 class per week",
      "2_week": "2 classes per week",
      "4_week": "4 classes per week",
      not_sure: "Not sure yet"
    }
  };

  function fieldValue(form, name) {
    var field = form.elements.namedItem(name);
    return field ? String(field.value || "").trim() : "";
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
    if (!target) return;
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

  function validationErrors(form) {
    var errors = [];
    var names = new Set();

    function add(name, message) {
      if (names.has(name)) return;
      names.add(name);
      errors.push([name, message]);
    }

    if (!form.checkValidity()) {
      form.querySelectorAll(":invalid").forEach(function (field) {
        if (!field.name) return;
        add(field.name, field.validationMessage || "Complete this required field.");
      });
    }

    [
      ["contact_role", "Select the adult contact role."],
      ["contact_name", "Enter the adult contact name."],
      ["country_timezone", "Enter the country or time zone."],
      ["learner_age_group", "Select the learner age group."],
      ["program", "Select a program."],
      ["frequency", "Select a preferred class frequency."],
      ["preferred_schedule", "Enter preferred days, time windows and time-zone context."]
    ].forEach(function (item) {
      if (!fieldValue(form, item[0])) add(item[0], item[1]);
    });

    Object.keys(labels).forEach(function (name) {
      var value = fieldValue(form, name);
      if (value && !Object.prototype.hasOwnProperty.call(labels[name], value)) {
        add(name, "Select a valid option for this field.");
      }
    });

    Object.keys(fieldLimits).forEach(function (name) {
      var value = fieldValue(form, name);
      if (value.length > fieldLimits[name]) {
        add(name, "Keep this field to " + fieldLimits[name] + " characters or fewer.");
      }
    });

    var role = fieldValue(form, "contact_role");
    var group = fieldValue(form, "learner_age_group");
    var program = fieldValue(form, "program");
    if (role === "adult_woman" && group && group !== "adult_woman") {
      add("learner_age_group", "An adult woman learner must select Adult woman as the learner age group.");
    }
    if (role === "parent_guardian" && group === "adult_woman") {
      add("learner_age_group", "A parent or guardian should select one of the child age groups.");
    }
    if (group === "adult_woman" && program === "culture_ethics") {
      add("program", "Afghan Culture & Islamic Ethics is currently available for learners aged 5–16.");
    }
    return errors;
  }

  function buildMessage(form) {
    var goal = fieldValue(form, "learning_goal") || "Not provided";
    return [
      "Hello Salaam Center,",
      "",
      "I would like to request a free 40-minute trial.",
      "",
      "Contact role: " + labels.contact_role[fieldValue(form, "contact_role")],
      "Contact name: " + fieldValue(form, "contact_name"),
      "Country / time zone: " + fieldValue(form, "country_timezone"),
      "Learner age group: " + labels.learner_age_group[fieldValue(form, "learner_age_group")],
      "Program: " + labels.program[fieldValue(form, "program")],
      "Preferred frequency: " + labels.frequency[fieldValue(form, "frequency")],
      "Preferred schedule: " + fieldValue(form, "preferred_schedule"),
      "Learning goal: " + goal,
      "",
      "I understand that teacher and schedule availability must be confirmed before the trial."
    ].join("\n");
  }

  function openWhatsApp(url) {
    var popup = null;
    try {
      popup = window.open(url, "_blank");
    } catch (error) {
      popup = null;
    }
    if (popup) {
      try {
        popup.opener = null;
      } catch (error) {
        // The new browsing context is already separate in this case.
      }
      return true;
    }
    try {
      window.location.assign(url);
      return true;
    } catch (error) {
      return false;
    }
  }

  function initialiseForm(form) {
    var button = form.querySelector("[data-whatsapp-submit]");
    var summary = document.getElementById("error-summary");
    if (!button || !summary) return;
    var activating = false;

    function restoreButton() {
      activating = false;
      button.disabled = false;
      button.textContent = buttonLabel;
      form.removeAttribute("aria-busy");
    }

    button.addEventListener("click", function () {
      if (activating) return;
      clearErrors(form, summary);
      var errors = validationErrors(form);
      if (errors.length) {
        errors.forEach(function (item) {
          showFieldError(form, item[0], item[1]);
        });
        showSummary(summary, errors.map(function (item) { return item[1]; }));
        return;
      }

      activating = true;
      button.disabled = true;
      button.textContent = "Opening WhatsApp…";
      form.setAttribute("aria-busy", "true");
      var message = buildMessage(form);
      var url = whatsappBaseUrl + encodeURIComponent(message);
      if (!openWhatsApp(url)) {
        restoreButton();
        showSummary(summary, ["This browser could not open WhatsApp. Use the generic WhatsApp link below and start a new message."]);
        return;
      }
      window.setTimeout(restoreButton, 1500);
    });
  }

  var form = document.querySelector("[data-trial-form]");
  if (form) initialiseForm(form);
}());
