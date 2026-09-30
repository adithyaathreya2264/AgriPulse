import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import App from "./App";

const STATES = ["Karnataka", "Kerala", "Tamil Nadu"];

const ONBOARDED_USER = {
  id: 7,
  user_code: "9810",
  phone: "9876543210",
  name: "Ramu Gowda",
  role: "owner",
  onboarded: true,
  dob: "1990-05-15",
  age: 36,
  state: "Karnataka",
  district: "Mandya",
  language: "en",
};

const NEW_USER = {
  id: 7,
  user_code: "9810",
  phone: "9876543210",
  name: "",
  role: "renter",
  onboarded: false,
};

// A tiny fake backend: "url-part METHOD" -> {status, body}
const mockBackend = (routes = {}) => {
  const calls = [];

  global.fetch = jest.fn((url, options = {}) => {
    const method = (options.method || "GET").toUpperCase();
    calls.push({ url: String(url), method, body: options.body });

    const key = Object.keys(routes).find((route) => {
      const [part, routeMethod] = route.split(" ");
      return String(url).includes(part) && (routeMethod || "GET") === method;
    });

    const { status, body } = key ? routes[key] : { status: 200, body: [] };

    return Promise.resolve({
      ok: status < 400,
      status,
      json: () => Promise.resolve(body),
    });
  });

  return calls;
};

const SEND_OTP = {
  "/auth/send-otp POST": { status: 200, body: { demo: true, demo_otp: "123456" } },
};

const REGIONS = {
  "/auth/regions": {
    status: 200,
    body: { states: STATES, districts: { Karnataka: ["Mandya", "Kolar"] } },
  },
};

const verifyReply = (user, isNew) => ({
  "/auth/verify-otp POST": {
    status: 200,
    body: {
      token: "the-token",
      is_new_user: isNew,
      onboarding_required: !user.onboarded,
      user,
    },
  },
});

const signIn = (user = ONBOARDED_USER, routes = {}) => {
  localStorage.setItem("token", "valid");
  localStorage.setItem("user", JSON.stringify(user));

  return mockBackend({ "/auth/me": { status: 200, body: user }, ...routes });
};

beforeEach(() => {
  localStorage.clear();
  mockBackend();
});

// ---------------------------------------------------------------- helpers
const openMenu = async () => {
  fireEvent.click(screen.getByLabelText("Open menu"));

  return screen.findByRole("navigation", { name: "Main" });
};

// Open a page through the hidden menu, like a farmer would
const openPage = async (label) => {
  const nav = await openMenu();

  fireEvent.click(within(nav).getByRole("button", { name: new RegExp(label) }));
};

const openProfile = async () => {
  fireEvent.click(screen.getByLabelText("Open profile"));

  return screen.findByRole("complementary", { name: "Profile" });
};

// let a running page transition finish (a second one is ignored while it plays)
const settle = () => new Promise((resolve) => setTimeout(resolve, 1000));

const openLogin = async () => {
  render(<App />);
  fireEvent.click(screen.getByText("GET STARTED"));

  // the colour transition runs first
  await screen.findByRole("heading", { name: "Login" });
  await settle();
};

const enterPhone = (phone = "9876543210") => {
  fireEvent.change(screen.getByPlaceholderText("10 digit mobile number"), {
    target: { value: phone },
  });
  fireEvent.click(screen.getByText("Send OTP"));
};

const enterPhoneAndOtp = async (phone = "9876543210", otp = "123456") => {
  enterPhone(phone);

  fireEvent.change(await screen.findByLabelText("6 digit OTP"), {
    target: { value: otp },
  });
  fireEvent.click(screen.getByText("Verify & continue"));
};

// ---------------------------------------------------------------------------
// Splash, information page, menu and profile
// ---------------------------------------------------------------------------

test("the splash shows the AgriPulse name first", () => {
  render(<App />);

  const splash = screen.getByRole("status", { name: "AgriPulse is loading" });

  expect(splash).toHaveTextContent("AGRIPULSE");
});

test("after the splash the visitor lands on the scrollable information page", () => {
  render(<App />);

  expect(screen.getByRole("heading", { level: 1 })).toHaveAccessibleName("Your trusted partner in every season");

  // the sections of the story
  for (const section of ["ABOUT US", "WHAT YOU CAN DO", "HOW IT WORKS", "EVERY LANGUAGE"]) {
    expect(screen.getByText(section)).toBeInTheDocument();
  }

  // the menu is hidden until it is opened
  expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
});

test("a saved page does not skip the information page", () => {
  localStorage.setItem("page", "marketplace");

  render(<App />);

  expect(screen.getByText("ABOUT US")).toBeInTheDocument();
});

test("the menu opens from the top left and lists every tool", async () => {
  render(<App />);

  const nav = await openMenu();

  for (const name of [
    "Disease Detection",
    "Price Prediction",
    "Weather",
    "Marketplace",
    "AI Assistant",
    "Loan Advisor",
    "Dashboard",
    "History",
  ]) {
    expect(within(nav).getByRole("button", { name: new RegExp(name) })).toBeInTheDocument();
  }

  // and closes again
  fireEvent.click(screen.getByLabelText("Close menu"));

  await waitFor(() => expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument(), {
    timeout: 4000,
  });
});

test("the profile opens from the top right and invites a guest to log in", async () => {
  render(<App />);

  const panel = await openProfile();

  expect(within(panel).getByText("Welcome, farmer")).toBeInTheDocument();
  expect(within(panel).getByRole("button", { name: /Login/ })).toBeInTheDocument();
});

test("only one panel is open at a time", async () => {
  render(<App />);

  await openMenu();
  fireEvent.click(screen.getByLabelText("Open profile"));

  expect(await screen.findByRole("complementary", { name: "Profile" })).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument(), {
    timeout: 4000,
  });
});

test("a tool asks a guest to log in first, then opens where they were going", async () => {
  mockBackend({ ...SEND_OTP, ...verifyReply(ONBOARDED_USER, false) });

  render(<App />);

  await openPage("Weather");

  expect(await screen.findByRole("heading", { name: "Login" })).toBeInTheDocument();
  await settle();

  await enterPhoneAndOtp();

  expect(await screen.findByPlaceholderText("Enter city name")).toBeInTheDocument();
});

test("the login screen can go back to the information page", async () => {
  await openLogin();

  fireEvent.click(screen.getByText("Back to AgriPulse"));

  expect(await screen.findByText("ABOUT US")).toBeInTheDocument();
});

// ---------------------------------------------------------------------------
// Login
// ---------------------------------------------------------------------------

test("login asks for a mobile number first", async () => {
  await openLogin();

  expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument();
  expect(screen.getByPlaceholderText("10 digit mobile number")).toBeInTheDocument();
  expect(screen.getByText("Send OTP")).toBeInTheDocument();
});

test("a short mobile number is rejected before anything is sent", async () => {
  const calls = mockBackend({});

  await openLogin();
  enterPhone("12345");

  expect(screen.getByText("Enter your 10 digit mobile number")).toBeInTheDocument();
  expect(calls.some((call) => call.url.includes("/auth/send-otp"))).toBe(false);
});

test("the demo OTP is shown after sending it and can be filled in", async () => {
  mockBackend({ ...SEND_OTP });

  await openLogin();
  enterPhone();

  expect(await screen.findByText(/Demo mode: the OTP is/)).toBeInTheDocument();
  expect(screen.getByText("123456")).toBeInTheDocument();

  fireEvent.click(screen.getByText("Fill it"));

  expect(screen.getByLabelText("6 digit OTP").value).toBe("123456");
});

test("a wrong OTP shows an error and does not log in", async () => {
  mockBackend({
    ...SEND_OTP,
    "/auth/verify-otp POST": { status: 401, body: { detail: "Wrong OTP" } },
  });

  await openLogin();
  await enterPhoneAndOtp("9876543210", "000000");

  expect(await screen.findByText("Wrong OTP")).toBeInTheDocument();
  expect(localStorage.getItem("token")).toBeNull();
});

test("the OTP step lets the farmer go back and change the number", async () => {
  mockBackend({ ...SEND_OTP });

  await openLogin();
  enterPhone();

  fireEvent.click(await screen.findByText("Change mobile number"));

  expect(await screen.findByPlaceholderText("10 digit mobile number")).toBeInTheDocument();
});

// ---------------------------------------------------------------------------
// Onboarding
// ---------------------------------------------------------------------------

test("a new farmer answers the onboarding questions once", async () => {
  const calls = mockBackend({
    ...SEND_OTP,
    ...REGIONS,
    ...verifyReply(NEW_USER, true),
    "/auth/profile PUT": { status: 200, body: ONBOARDED_USER },
  });

  await openLogin();
  await enterPhoneAndOtp();

  expect(await screen.findByText("Tell us about yourself")).toBeInTheDocument();

  // step 1: about you
  fireEvent.change(screen.getByPlaceholderText("Your name"), { target: { value: "Ramu Gowda" } });
  fireEvent.change(screen.getByLabelText("Date of birth *"), { target: { value: "1990-05-15" } });

  // the age is worked out from the date of birth
  expect(screen.getByLabelText("Age").value).toMatch(/^[0-9]+$/);

  fireEvent.click(screen.getByText("Continue"));

  // step 2: the farm
  fireEvent.change(await screen.findByLabelText("State *"), { target: { value: "Karnataka" } });
  fireEvent.change(screen.getByPlaceholderText("Your district"), { target: { value: "Mandya" } });
  fireEvent.click(screen.getByText("Continue"));

  // step 3: preferences
  fireEvent.click(await screen.findByText("I own equipment"));
  fireEvent.click(screen.getByText("Finish"));

  await waitFor(() => expect(JSON.parse(localStorage.getItem("user")).name).toBe("Ramu Gowda"));

  const save = calls.find((call) => call.url.includes("/auth/profile"));

  expect(JSON.parse(save.body)).toMatchObject({
    name: "Ramu Gowda",
    dob: "1990-05-15",
    state: "Karnataka",
    district: "Mandya",
    role: "owner",
  });

  expect(localStorage.getItem("token")).toBe("the-token");
  // and lands on the dashboard
  expect(await screen.findByText(/Namaste,/)).toBeInTheDocument();
  expect(screen.queryByText("Tell us about yourself")).not.toBeInTheDocument();
});

test("onboarding will not continue with missing answers", async () => {
  const calls = mockBackend({ ...SEND_OTP, ...REGIONS, ...verifyReply(NEW_USER, true) });

  await openLogin();
  await enterPhoneAndOtp();

  await screen.findByText("Tell us about yourself");

  fireEvent.click(screen.getByText("Continue"));
  expect(screen.getByText("Please enter your name")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("Your name"), { target: { value: "Ramu" } });
  fireEvent.click(screen.getByText("Continue"));
  expect(screen.getByText("Please enter your date of birth")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Date of birth *"), { target: { value: "1990-05-15" } });
  fireEvent.click(screen.getByText("Continue"));

  await screen.findByLabelText("State *");
  fireEvent.click(screen.getByText("Continue"));
  expect(screen.getByText("Please choose your state")).toBeInTheDocument();

  expect(calls.some((call) => call.url.includes("/auth/profile"))).toBe(false);
});

test("a farmer who has not finished onboarding is sent back to it", async () => {
  signIn(NEW_USER, REGIONS);

  render(<App />);

  await openPage("Disease Detection");

  expect(await screen.findByText("Tell us about yourself")).toBeInTheDocument();
});

// ---------------------------------------------------------------------------
// Signed in
// ---------------------------------------------------------------------------

test("a returning farmer goes straight to the dashboard with the saved profile", async () => {
  mockBackend({ ...SEND_OTP, ...verifyReply(ONBOARDED_USER, false) });

  await openLogin();
  await enterPhoneAndOtp();

  expect(await screen.findByText(/Namaste,/)).toBeInTheDocument();
  expect(screen.queryByText("Tell us about yourself")).not.toBeInTheDocument();

  expect(JSON.parse(localStorage.getItem("user"))).toMatchObject({
    name: "Ramu Gowda",
    district: "Mandya",
    state: "Karnataka",
  });
});

test("the header shows the signed-in farmer", async () => {
  signIn();

  render(<App />);

  expect(await screen.findByText("Ramu")).toBeInTheDocument();

  const panel = await openProfile();

  expect(within(panel).getByText("Ramu Gowda")).toBeInTheDocument();
  expect(within(panel).getByText("ID #9810")).toBeInTheDocument();
  expect(within(panel).getByText("+91 9876543210")).toBeInTheDocument();
});

test("the dashboard greets the farmer and offers every feature", async () => {
  signIn();

  render(<App />);

  await openPage("Dashboard");

  const heading = await screen.findByRole("heading", { level: 1, name: /Namaste/ });

  expect(heading).toHaveTextContent("Namaste, Ramu");
  expect(screen.getAllByText("Disease Detection").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Loan Advisor").length).toBeGreaterThan(0);
});

test("the language saved in the profile is applied after login", async () => {
  mockBackend({
    ...SEND_OTP,
    ...verifyReply({ ...ONBOARDED_USER, language: "kn" }, false),
  });

  await openLogin();
  await enterPhoneAndOtp();

  await screen.findByText(/Namaste,/);

  const nav = await openMenu();

  expect(within(nav).getByText("ಹವಾಮಾನ")).toBeInTheDocument();
  expect(localStorage.getItem("lang")).toBe("kn");
});

test("an expired session logs the farmer out quietly", async () => {
  signIn(ONBOARDED_USER, { "/auth/me": { status: 401, body: { detail: "Invalid or expired token" } } });

  render(<App />);

  await waitFor(() => expect(localStorage.getItem("token")).toBeNull());

  const panel = await openProfile();

  expect(within(panel).getByText("Welcome, farmer")).toBeInTheDocument();
});

test("logging out clears the session and returns to the information page", async () => {
  signIn();

  render(<App />);

  const panel = await openProfile();

  fireEvent.click(within(panel).getByRole("button", { name: /Logout/ }));

  expect(localStorage.getItem("token")).toBeNull();
  expect(await screen.findByText("ABOUT US")).toBeInTheDocument();
});

test("the profile page shows the saved answers for editing", async () => {
  signIn(ONBOARDED_USER, REGIONS);

  render(<App />);

  const panel = await openProfile();

  fireEvent.click(within(panel).getByRole("button", { name: /Edit profile/ }));

  expect(await screen.findByText("Your profile")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("Your name").value).toBe("Ramu Gowda");
  expect(screen.getByPlaceholderText("Your district").value).toBe("Mandya");
});

// ---------------------------------------------------------------------------
// Language and voice
// ---------------------------------------------------------------------------

test("the menu offers at least 12 languages", async () => {
  render(<App />);

  const nav = await openMenu();
  const group = within(nav).getByRole("group", { name: "Language of the answers" });

  expect(within(group).getAllByRole("button").length).toBeGreaterThanOrEqual(12);
});

test("choosing a language translates the navigation and is remembered", async () => {
  render(<App />);

  const nav = await openMenu();

  expect(within(nav).getByText("Weather")).toBeInTheDocument();

  fireEvent.click(within(nav).getByRole("button", { name: "ಕನ್ನಡ" }));

  expect(await within(nav).findByText("ಹವಾಮಾನ")).toBeInTheDocument();
  expect(within(nav).queryByText("Weather")).not.toBeInTheDocument();
  expect(localStorage.getItem("lang")).toBe("kn");
});

test("Bengali, Gujarati, Punjabi, Odia, Urdu, Assamese and Bhojpuri are translated", async () => {
  render(<App />);

  const expected = [
    ["বাংলা", "আবহাওয়া"],
    ["ગુજરાતી", "હવામાન"],
    ["ਪੰਜਾਬੀ", "ਮੌਸਮ"],
    ["ଓଡ଼ିଆ", "ପାଣିପାଗ"],
    ["اردو", "موسم"],
    ["অসমীয়া", "বতৰ"],
    ["भोजपुरी", "मौसम"],
  ];

  const nav = await openMenu();

  for (const [name, weather] of expected) {
    fireEvent.click(within(nav).getByRole("button", { name }));

    expect(await within(nav).findByText(weather)).toBeInTheDocument();
    expect(within(nav).queryByText("Weather")).not.toBeInTheDocument();
  }

  // Urdu reads right to left, the others left to right
  fireEvent.click(within(nav).getByRole("button", { name: "اردو" }));
  expect(document.documentElement.getAttribute("dir")).toBe("rtl");

  fireEvent.click(within(nav).getByRole("button", { name: "বাংলা" }));
  expect(document.documentElement.getAttribute("dir")).toBe("ltr");
});

test("languages without a label file are translated by the server", async () => {
  mockBackend({
    "/i18n/translate POST": { status: 200, body: { labels: { nav_weather: "കാലാവസ്ഥ" } } },
  });

  render(<App />);

  const nav = await openMenu();

  fireEvent.click(within(nav).getByRole("button", { name: "മലയാളം" }));

  expect(await within(nav).findByText("കാലാവസ്ഥ")).toBeInTheDocument();

  const call = global.fetch.mock.calls.find(([url]) => String(url).includes("/i18n/translate"));

  expect(JSON.parse(call[1].body).lang).toBe("ml");
});

test("a voice command button is available inside the tools once signed in", async () => {
  signIn();

  render(<App />);

  expect(screen.queryByRole("button", { name: "Speak a command" })).not.toBeInTheDocument();

  await openPage("Dashboard");

  expect(await screen.findByRole("button", { name: "Speak a command" })).toBeInTheDocument();
});

test("the theme can be switched to dark from the profile panel and is remembered", async () => {
  render(<App />);

  const panel = await openProfile();

  fireEvent.click(within(panel).getByLabelText("Switch to dark mode"));

  expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  expect(localStorage.getItem("theme")).toBe("dark");
});

// ---------------------------------------------------------------------------
// Pages
// ---------------------------------------------------------------------------

test("the menu opens the price page", async () => {
  signIn();

  render(<App />);

  await openPage("Price Prediction");

  expect(await screen.findByPlaceholderText("Search crop...")).toBeInTheDocument();
});

test("the disease page asks for a leaf photo", async () => {
  signIn();

  render(<App />);

  await openPage("Disease Detection");

  expect(await screen.findByText("Drop a leaf photo here")).toBeInTheDocument();
  expect(screen.getByText("Diagnose").closest("button")).toBeDisabled();
});

test("the marketplace lists equipment from the server", async () => {
  signIn(ONBOARDED_USER, {
    "/equipment GET": {
      status: 200,
      body: [
        {
          id: 1,
          equipment_name: "Mahindra 575 Tractor",
          owner_name: "Suresh",
          owner_id: 99,
          location: "Mandya",
          category: "Tractor",
          price_per_day: 1800,
          availability: "Available",
          contact_number: "9000000000",
        },
      ],
    },
  });

  render(<App />);

  await openPage("Marketplace");

  expect(await screen.findByText("Mahindra 575 Tractor")).toBeInTheDocument();
  expect(screen.getByText("Rent Equipment")).toBeInTheDocument();
});

test("loan advisor shows the form to a signed-in farmer", async () => {
  signIn(ONBOARDED_USER, { "/loan/profile": { status: 404, body: {} } });

  render(<App />);

  await openPage("Loan Advisor");

  expect(await screen.findByText("1. Farm & land")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("District *")).toBeInTheDocument();
  expect(screen.getByText("Fetch from DigiLocker (demo)")).toBeInTheDocument();

  fireEvent.click(screen.getByText("Next"));

  expect(await screen.findByText(/Crops you grew/)).toBeInTheDocument();
});

test("the assistant offers starter questions", async () => {
  signIn();

  render(<App />);

  await openPage("AI Assistant");

  expect(await screen.findByText("AgriPulse AI")).toBeInTheDocument();
  expect(screen.getByText("How do I control aphids on chilli?")).toBeInTheDocument();
});

test("the history page shows an empty state", async () => {
  signIn(ONBOARDED_USER, { "/predictions GET": { status: 200, body: [] } });

  render(<App />);

  await openPage("History");

  expect(await screen.findByText("No scans yet")).toBeInTheDocument();
});
