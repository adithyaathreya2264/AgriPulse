import { directImageUrl } from "./marketplaceParts";

const DRIVE = "https://drive.google.com/thumbnail?id=1AbC-_dEf123&sz=w1000";

test("Google Drive share links become direct image links", () => {
  expect(directImageUrl("https://drive.google.com/file/d/1AbC-_dEf123/view?usp=sharing")).toBe(DRIVE);
  expect(directImageUrl("https://drive.google.com/open?id=1AbC-_dEf123")).toBe(DRIVE);
  expect(directImageUrl("https://drive.google.com/uc?export=view&id=1AbC-_dEf123")).toBe(DRIVE);
  expect(directImageUrl("  https://drive.google.com/file/d/1AbC-_dEf123/view  ")).toBe(DRIVE);
});

test("other links are left alone", () => {
  expect(directImageUrl("https://example.com/tractor.jpg")).toBe("https://example.com/tractor.jpg");
  expect(directImageUrl("")).toBe("");
  expect(directImageUrl(undefined)).toBe("");
});
