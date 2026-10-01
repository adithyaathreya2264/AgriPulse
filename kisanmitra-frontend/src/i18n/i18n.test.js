import en from "./en.json";
import { LANGUAGES, enumText, makeT, missingLabels, serverText } from "./index";

const PLACEHOLDER = /\{\w+\}/g;

describe("every language is complete", () => {
  test.each(LANGUAGES.filter((item) => item.code !== "en").map((item) => [item.code]))(
    "%s has a translation for every label",
    (code) => {
      expect(Object.keys(missingLabels(code))).toEqual([]);
    }
  );

  test.each(LANGUAGES.filter((item) => item.code !== "en").map((item) => [item.code]))(
    "%s keeps the {placeholders} of the English text",
    (code) => {
      // t() with no params returns the raw sentence, so the braces can be compared
      const t = makeT(code);

      const broken = Object.keys(en).filter((key) => {
        const wanted = (en[key].match(PLACEHOLDER) || []).sort().join();
        const found = (t(key).match(PLACEHOLDER) || []).sort().join();

        return wanted !== found;
      });

      expect(broken).toEqual([]);
    }
  );
});

describe("t()", () => {
  test("fills {placeholders}", () => {
    const t = makeT("en");

    expect(t("auth.resend_in", { seconds: 12 })).toBe("Resend in 12s");
  });

  test("falls back to English, then to the key", () => {
    const t = makeT("hi", {});

    expect(t("no.such.key")).toBe("no.such.key");
  });

  test("a translated language does not show English", () => {
    const t = makeT("kn");

    expect(t("landing.get_started")).not.toBe(en["landing.get_started"]);
  });
});

describe("server messages and statuses", () => {
  test("a known server error is translated", () => {
    const t = makeT("hi");

    expect(serverText(t, "Wrong OTP")).not.toBe("Wrong OTP");
    expect(serverText(t, "Something the server invented")).toBe("Something the server invented");
  });

  test("statuses and categories use their labels", () => {
    const t = makeT("hi");

    expect(enumText(t, "status.", "Confirmed")).not.toBe("Confirmed");
    expect(enumText(t, "cat.", "Sprayer Drone")).not.toBe("Sprayer Drone");
    expect(enumText(t, "status.", "Mystery")).toBe("Mystery");
  });
});
