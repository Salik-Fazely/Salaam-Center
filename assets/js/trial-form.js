(function () {
  "use strict";

  var whatsappBaseUrl = "https://wa.me/34614401172?text=";
  var language = document.documentElement && document.documentElement.lang === "fa-AF"
    ? "fa-AF"
    : "en";
  var fieldLimits = {
    contact_name: 80,
    country_timezone: 100,
    preferred_schedule: 400,
    learning_goal: 500
  };
  var locales = {
    en: {
      button: "Continue in WhatsApp",
      opening: "Opening WhatsApp…",
      summaryPrefix: "Please review: ",
      notProvided: "Not provided",
      options: {
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
      },
      required: {
        contact_role: "Select the adult contact role.",
        contact_name: "Enter the adult contact name.",
        country_timezone: "Enter the country or time zone.",
        learner_age_group: "Select the learner age group.",
        program: "Select a program.",
        frequency: "Select a preferred class frequency.",
        preferred_schedule: "Enter preferred days, time windows and time-zone context."
      },
      invalidOption: "Select a valid option for this field.",
      limit: function (limit) {
        return "Keep this field to " + limit + " characters or fewer.";
      },
      adultMismatch: "An adult woman learner must select Adult woman as the learner age group.",
      guardianMismatch: "A parent or guardian should select one of the child age groups.",
      cultureMismatch: "Afghan Culture & Islamic Ethics is currently available for learners aged 5–16.",
      openFailure: "This browser could not open WhatsApp. Use the generic WhatsApp link below and start a new message.",
      message: function (values, options) {
        return [
          "Hello Salaam Center,",
          "",
          "I would like to request a free 40-minute trial.",
          "",
          "Contact role: " + options.contact_role[values.contact_role],
          "Contact name: " + values.contact_name,
          "Country / time zone: " + values.country_timezone,
          "Learner age group: " + options.learner_age_group[values.learner_age_group],
          "Program: " + options.program[values.program],
          "Preferred frequency: " + options.frequency[values.frequency],
          "Preferred schedule: " + values.preferred_schedule,
          "Learning goal: " + values.learning_goal,
          "",
          "I understand that teacher and schedule availability must be confirmed before the trial."
        ].join("\n");
      }
    },
    "fa-AF": {
      button: "ادامه در واتس‌اپ",
      opening: "در حال باز کردن واتس‌اپ…",
      summaryPrefix: "لطفاً بررسی کنید: ",
      notProvided: "ذکر نشده",
      options: {
        contact_role: {
          parent_guardian: "والد یا سرپرست",
          adult_woman: "شاگرد زن بزرگ‌سال"
        },
        learner_age_group: {
          age_5_7: "5 تا 7 سال",
          age_8_11: "8 تا 11 سال",
          age_12_16: "12 تا 16 سال",
          adult_woman: "زن بزرگ‌سال"
        },
        program: {
          quran: "قرآن",
          dari_persian: "دری",
          culture_ethics: "فرهنگ افغان و اخلاق اسلامی"
        },
        frequency: {
          "1_week": "1 صنف در هفته",
          "2_week": "2 صنف در هفته",
          "4_week": "4 صنف در هفته",
          not_sure: "هنوز مطمئن نیستم"
        }
      },
      required: {
        contact_role: "نقش شخص تماس‌گیرندهٔ بزرگ‌سال را انتخاب کنید.",
        contact_name: "نام شخص تماس‌گیرندهٔ بزرگ‌سال را وارد کنید.",
        country_timezone: "کشور یا منطقهٔ زمانی را وارد کنید.",
        learner_age_group: "گروه سنی شاگرد را انتخاب کنید.",
        program: "یک برنامه را انتخاب کنید.",
        frequency: "تعداد صنف در هفته را انتخاب کنید.",
        preferred_schedule: "روزها، ساعت‌ها و منطقهٔ زمانی دلخواه را وارد کنید."
      },
      invalidOption: "برای این بخش یک گزینهٔ معتبر را انتخاب کنید.",
      limit: function (limit) {
        return "این بخش را به " + limit + " نویسه یا کمتر محدود کنید.";
      },
      adultMismatch: "شاگرد زن بزرگ‌سال باید گروه سنی زن بزرگ‌سال را انتخاب کند.",
      guardianMismatch: "والد یا سرپرست باید یکی از گروه‌های سنی کودک را انتخاب کند.",
      cultureMismatch: "برنامهٔ فرهنگ افغان و اخلاق اسلامی اکنون برای شاگردان 5 تا 16 ساله ارائه می‌شود.",
      openFailure: "این مرورگر نتوانست واتس‌اپ را باز کند. از پیوند عمومی واتس‌اپ در پایین استفاده کنید و پیام تازه‌ای بنویسید.",
      message: function (values, options) {
        return [
          "سلام Salaam Center،",
          "",
          "می‌خواهم برای یک جلسهٔ آزمایشی رایگان 40 دقیقه‌ای درخواست بدهم.",
          "",
          "نقش تماس‌گیرنده: " + options.contact_role[values.contact_role],
          "نام شخص تماس‌گیرنده: " + values.contact_name,
          "کشور / منطقهٔ زمانی: " + values.country_timezone,
          "گروه سنی شاگرد: " + options.learner_age_group[values.learner_age_group],
          "برنامه: " + options.program[values.program],
          "تعداد صنف در هفته: " + options.frequency[values.frequency],
          "زمان‌های ترجیحی: " + values.preferred_schedule,
          "هدف آموزشی: " + values.learning_goal,
          "",
          "می‌دانم که استاد و زمان جلسه باید پیش از برگزاری تأیید شوند."
        ].join("\n");
      }
    }
  };
  var locale = locales[language];
  var labels = locale.options;

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
    summary.textContent = locale.summaryPrefix + messages.join(" ");
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
        var message = language === "fa-AF"
          ? (locale.required[field.name] || locale.invalidOption)
          : (field.validationMessage || "Complete this required field.");
        add(field.name, message);
      });
    }

    Object.keys(locale.required).forEach(function (name) {
      if (!fieldValue(form, name)) add(name, locale.required[name]);
    });

    Object.keys(labels).forEach(function (name) {
      var value = fieldValue(form, name);
      if (value && !Object.prototype.hasOwnProperty.call(labels[name], value)) {
        add(name, locale.invalidOption);
      }
    });

    Object.keys(fieldLimits).forEach(function (name) {
      var value = fieldValue(form, name);
      if (value.length > fieldLimits[name]) add(name, locale.limit(fieldLimits[name]));
    });

    var role = fieldValue(form, "contact_role");
    var group = fieldValue(form, "learner_age_group");
    var program = fieldValue(form, "program");
    if (role === "adult_woman" && group && group !== "adult_woman") {
      add("learner_age_group", locale.adultMismatch);
    }
    if (role === "parent_guardian" && group === "adult_woman") {
      add("learner_age_group", locale.guardianMismatch);
    }
    if (group === "adult_woman" && program === "culture_ethics") {
      add("program", locale.cultureMismatch);
    }
    return errors;
  }

  function buildMessage(form) {
    var values = {
      contact_role: fieldValue(form, "contact_role"),
      contact_name: fieldValue(form, "contact_name"),
      country_timezone: fieldValue(form, "country_timezone"),
      learner_age_group: fieldValue(form, "learner_age_group"),
      program: fieldValue(form, "program"),
      frequency: fieldValue(form, "frequency"),
      preferred_schedule: fieldValue(form, "preferred_schedule"),
      learning_goal: fieldValue(form, "learning_goal") || locale.notProvided
    };
    return locale.message(values, labels);
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
      button.textContent = locale.button;
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
      button.textContent = locale.opening;
      form.setAttribute("aria-busy", "true");
      var message = buildMessage(form);
      var url = whatsappBaseUrl + encodeURIComponent(message);
      if (!openWhatsApp(url)) {
        restoreButton();
        showSummary(summary, [locale.openFailure]);
        return;
      }
      window.setTimeout(restoreButton, 1500);
    });
  }

  var form = document.querySelector("[data-trial-form]");
  if (form) initialiseForm(form);
}());
