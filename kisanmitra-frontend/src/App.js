/*import { useState } from "react";*/

import "./App.css";
import { useState, useEffect, useRef } from "react";

function App() {
  const [page, setPage] = useState(localStorage.getItem("page") || "home");

  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  const [history, setHistory] = useState([]);

  const [equipment, setEquipment] = useState([]);
  const [crop, setCrop] = useState("");
  const [priceResult, setPriceResult] = useState(null);
  const [city, setCity] = useState("");
  const [diseaseCity, setDiseaseCity] = useState("");
  const [weatherResult, setWeatherResult] = useState(null);
  const [equipmentName, setEquipmentName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [location, setLocation] = useState("");
  const [pricePerDay, setPricePerDay] = useState("");
  const [contactNumber, setContactNumber] = useState("");
  const [stats, setStats] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [loadingChat, setLoadingChat] = useState(false);
  const chatEndRef = useRef(null);
  const [market, setMarket] = useState("");
  const [district, setDistrict] = useState("");
  const [marketOptions, setMarketOptions] = useState([]);
  const [marketSearch, setMarketSearch] = useState("");
  const [equipmentCategory, setEquipmentCategory] = useState("");
  const [equipmentDescription, setEquipmentDescription] = useState("");
  const [equipmentImage, setEquipmentImage] = useState("");

  const [showAddEquipment, setShowAddEquipment] = useState(false);
  const [selectedEquipment, setSelectedEquipment] = useState(null);

  const [renterName, setRenterName] = useState("");
  const [renterPhone, setRenterPhone] = useState("");
  const [rentalStartDate, setRentalStartDate] = useState("");
  const [rentalEndDate, setRentalEndDate] = useState("");

  const [marketplaceSearch, setMarketplaceSearch] = useState("");
  const [marketplaceCategory, setMarketplaceCategory] = useState("All");
  const [showCheckout, setShowCheckout] = useState(false);

  const searchMarkets = async () => {
    if (!crop.trim()) {
      setPriceResult({
        error: "Please enter a crop name"
      });
      return;
    }

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/predict-price?crop=${encodeURIComponent(crop)}`
      );

      const data = await response.json();

      console.log(data);

      if (data.error) {
        setMarketOptions([]);
        setPriceResult(data);
        return;
      }
      console.log("price result:", data);

      setMarketOptions(data.markets || []);
      setMarketSearch("");
      setMarket("");
      setDistrict("");
      setPriceResult(null);

    } catch (error) {
      console.error(error);

      setPriceResult({
        error: "Failed to fetch market data"
      });
    }
  };

  const loadDashboard = async () => {
    const res = await fetch("http://127.0.0.1:8000/dashboard-stats");
    const data = await res.json();
    setStats(data);
  };
  useEffect(() => {
    loadDashboard();
    fetchEquipment();
  }, []);
  useEffect(() => {
    localStorage.setItem("page", page);
  }, [page]);

  const addEquipment = async () => {
    if (
      !equipmentName.trim() ||
      !ownerName.trim() ||
      !location.trim() ||
      !pricePerDay ||
      !contactNumber.trim()
    ) {
      alert("Please fill all required fields");
      return;
    }

    try {
      const params = new URLSearchParams({
        equipment_name: equipmentName,
        owner_name: ownerName,
        price_per_day: pricePerDay,
        location: location,
        contact_number: contactNumber,
        category: equipmentCategory || "Other",
        description: equipmentDescription,
        image_url: equipmentImage,
      });

      const res = await fetch(
        `http://127.0.0.1:8000/equipment?${params.toString()}`,
        {
          method: "POST",
        }
      );

      const data = await res.json();

      if (!res.ok) {
        alert(data.detail || "Failed to add equipment");
        return;
      }

      alert("Equipment added successfully!");

      setEquipmentName("");
      setOwnerName("");
      setLocation("");
      setPricePerDay("");
      setContactNumber("");
      setEquipmentCategory("");
      setEquipmentDescription("");
      setEquipmentImage("");

      setShowAddEquipment(false);

      fetchEquipment();
    } catch (error) {
      console.error(error);
      alert("Failed to add equipment");
    }
  };

  // Disease Detection
  const handleUpload = async () => {
    if (!file) {
      alert("Please select an image");
      return;
    }
    if (!diseaseCity.trim()) {
      alert("Please enter your city");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    formData.append("city", diseaseCity);

    try {
      const res = await fetch(
        "http://127.0.0.1:8000/detect-disease",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await res.json();
      console.log(data);
      setResult(data);
      setChatMessages([
        {
          sender: "assistant",
          text:
            `Disease: ${data.report.disease}

            Confidence: ${data.report.confidence}%

            Medicine: ${data.report.medicine}

            Estimated Cost: ${data.report.estimated_cost}

            You can now ask me anything about this disease.`
        }
      ]);

      //setPage("assistant");
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    }
  };

  // History
  const fetchHistory = async () => {
    const res = await fetch(
      "http://127.0.0.1:8000/predictions"
    );

    const data = await res.json();

    setHistory(data);
  };

  const clearHistory = async () => {
    await fetch(
      "http://127.0.0.1:8000/predictions",
      {
        method: "DELETE",
      }
    );

    setHistory([]);
  };

  // Marketplace
  const fetchEquipment = async () => {
    const res = await fetch(
      "http://127.0.0.1:8000/equipment"
    );


    const data = await res.json();

    setEquipment(data);
  };

  const rentEquipment = async () => {
    if (!selectedEquipment) {
      alert("Please select equipment");
      return;
    }

    if (!renterName.trim() || !renterPhone.trim()) {
      alert("Please enter your name and phone number");
      return;
    }

    if (!rentalStartDate || !rentalEndDate) {
      alert("Please select rental dates");
      return;
    }

    try {
      // ========================================================
      // STEP 1: CREATE RENTAL
      // ========================================================

      const rentalParams = new URLSearchParams({
        equipment_id: selectedEquipment.id,
        renter_name: renterName,
        renter_phone: renterPhone,
        start_date: rentalStartDate,
        end_date: rentalEndDate,
      });

      const rentalResponse = await fetch(
        `http://127.0.0.1:8000/rent-equipment?${rentalParams.toString()}`,
        {
          method: "POST",
        }
      );

      const rentalData = await rentalResponse.json();

      if (!rentalResponse.ok) {
        alert(rentalData.detail || "Failed to create rental");
        return;
      }

      // ========================================================
      // STEP 2: CREATE RAZORPAY ORDER
      // ========================================================

      const paymentResponse = await fetch(
        `http://127.0.0.1:8000/create-payment-order?rental_id=${rentalData.rental_id}`,
        {
          method: "POST",
        }
      );

      const paymentData = await paymentResponse.json();

      if (!paymentResponse.ok) {
        alert(paymentData.detail || "Failed to create payment order");
        return;
      }

      // ========================================================
      // STEP 3: OPEN RAZORPAY CHECKOUT
      // ========================================================

      if (!window.Razorpay) {
        alert("Razorpay Checkout failed to load. Please refresh the page.");
        return;
      }

      const options = {
        key: paymentData.key_id,

        amount: paymentData.amount,

        currency: paymentData.currency,

        name: "AgriPulse",

        description: `Equipment Rental - ${selectedEquipment.equipment_name}`,

        order_id: paymentData.order_id,

        prefill: {
          name: renterName,
          contact: renterPhone,
        },

        notes: {
          rental_id: String(rentalData.rental_id),
          equipment: selectedEquipment.equipment_name,
        },

        theme: {
          color: "#2e7d32",
        },

        handler: async function (response) {
          // ====================================================
          // STEP 4: VERIFY PAYMENT ON BACKEND
          // ====================================================

          try {
            const verifyParams = new URLSearchParams({
              rental_id: String(rentalData.rental_id),
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });

            const verifyResponse = await fetch(
              `http://127.0.0.1:8000/verify-payment?${verifyParams.toString()}`,
              {
                method: "POST",
              }
            );

            const verifyData = await verifyResponse.json();

            if (!verifyResponse.ok) {
              alert(
                verifyData.detail ||
                "Payment verification failed"
              );
              return;
            }

            // ==================================================
            // PAYMENT SUCCESS
            // ==================================================

            alert(
              `Payment successful! 🎉\n\n` +
              `Equipment: ${selectedEquipment.equipment_name}\n` +
              `Rental ID: ${rentalData.rental_id}\n` +
              `Total Paid: ₹${rentalData.total_amount}\n\n` +
              `Your rental has been confirmed.`
            );

            setSelectedEquipment(null);
            setRenterName("");
            setRenterPhone("");
            setRentalStartDate("");
            setRentalEndDate("");

            fetchEquipment();

          } catch (error) {
            console.error(
              "Payment verification error:",
              error
            );

            alert(
              "Payment was completed, but verification failed. Please contact the administrator."
            );
          }
        },

        modal: {
          ondismiss: function () {
            console.log(
              "Razorpay checkout closed by user"
            );
          },
        },
      };

      const razorpay = new window.Razorpay(options);

      razorpay.on(
        "payment.failed",
        function (response) {
          console.error(
            "Payment failed:",
            response.error
          );

          alert(
            response.error.description ||
            "Payment failed. Please try again."
          );
        }
      );

      razorpay.open();

    } catch (error) {
      console.error(
        "Rental/payment error:",
        error
      );

      alert(
        "Something went wrong while processing the rental."
      );
    }
  };
  const calculateRentalDays = () => {
    if (!rentalStartDate || !rentalEndDate) {
      return 0;
    }

    const start = new Date(rentalStartDate);
    const end = new Date(rentalEndDate);

    const difference =
      (end - start) / (1000 * 60 * 60 * 24);

    return difference >= 0 ? difference + 1 : 0;
  };

  const rentalDays = calculateRentalDays();

  const rentalTotal =
    rentalDays > 0 && selectedEquipment
      ? rentalDays * Number(selectedEquipment.price_per_day)
      : 0;

  const predictPrice = async () => {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/predict-price?crop=${encodeURIComponent(crop)}&district=${encodeURIComponent(district)}&market=${encodeURIComponent(market)}`
      );

      const data = await response.json();
      console.log(data);

      setPriceResult(data);
    } catch (error) {
      setPriceResult({ error: "Failed to fetch price prediction" });
    }
  };

  const getWeather = async () => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/weather?city=${encodeURIComponent(city)}`
      );

      const data = await res.json();
      console.log(data);

      setWeatherResult(data);
    } catch (error) {
      console.error(error)
    }
  };
  const sendMessage = async () => {
    if (!chatInput.trim()) return;
    const question = chatInput;
    setChatMessages((prev) => [...prev, {
      sender: "user",
      text: question,
    },])
    setChatInput("");
    setLoadingChat(true);
    try {
      const res = await fetch(
        "http://127.0.0.1:8000/ai-chat",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: question,
          }),
        }
      );
      const data = await res.json();
      setChatMessages((prev) => [...prev, {
        sender: "assistant",
        text: data.answer || data.Message,
      },]);

    } catch (err) {
      console.error(err);
    }
    //setChatInput("");
    setLoadingChat(false);

  };
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [chatMessages]);

  return (
    <div className="app-container">

      {/* Navbar */}
      <div
        className="navbar"
      >
        <button className={`nav-btn ${page === "home" ? "active-nav" : ""}`} onClick={() => setPage("home")}>
          Home
        </button>

        <button className={`nav-btn ${page === "disease" ? "active-nav" : ""}`} onClick={() => setPage("disease")}>
          Disease Detection
        </button>

        <button className={`nav-btn ${page === "price" ? "active-nav" : ""}`} onClick={() => setPage("price")}>
          Price Prediction
        </button>

        <button className={`nav-btn ${page === "weather" ? "active-nav" : ""}`} onClick={() => setPage("weather")}>
          Weather
        </button>

        <button className={`nav-btn ${page === "marketplace" ? "active-nav" : ""}`} onClick={() => setPage("marketplace")}>
          Marketplace
        </button>

        <button className={`nav-btn ${page === "history" ? "active-nav" : ""}`} onClick={() => setPage("history")}>
          History
        </button>

        <button
          className={`nav-btn ${page === "assistant" ? "active-nav" : ""}`} onClick={() => setPage("assistant")}
        >
          AI Assistant
        </button>
      </div>

      {/* Home */}
      {page === "home" && (
        <div className="home-page">
          <div className="hero-section">

            <h1 className="hero-title">
              AgriPulse
            </h1>

            <h2 className="hero-subtitle">
              AI-Powered Smart Agriculture Platform
            </h2>

            <p className="hero-text">
              Helping farmers with crop disease detection,
              weather advisory, crop price prediction,
              multilingual support, Whatsapp assistance,
              and farm equipment rental services.
            </p>
            <div className="feature-badges">
              <span>Disease Detection </span>
              <span>Weather Advisory </span>
              <span>Price Prediction </span>
              <span>Equipment Rental </span>
            </div>
          </div>
          {stats && (
            <div className="dashboard-cards">

              <div className="dashboard-card">
                <h3>Predictions</h3>
                <h2>{stats.total_predictions}</h2>
              </div>

              <div className="dashboard-card">
                <h3>Equipment</h3>
                <h2>{stats.total_equipment}</h2>
              </div>

              <div className="dashboard-card">
                <h3>Rentals</h3>
                <h2>{stats.total_rentals}</h2>
              </div>

              <div className="dashboard-card">
                <h3>Users</h3>
                <h2>{stats.total_users}</h2>
              </div>

            </div>
          )}
          <h2 className="featured-title">Featured Equipment</h2>
          <div className="featured-equipment">
            {[...equipment].sort((a, b) =>
              a.availability === "Available" &&
                b.availability !== "Available" ? -1 : a.availability !== "Available" &&
                  b.availability === "Available" ? 1 : 0).map((item) => (
                    <div key={item.id} className="featured-card">
                      <h3>{item.equipment_name}</h3>
                      <p>{item.location}</p>
                      <p>₹{item.price_per_day}/day</p>
                      <p>Status:
                        <span className={
                          item.availability === "Available"
                            ? "status-available"
                            : "status-rented"
                        }
                        >
                          {" "}{item.availability}
                        </span>
                      </p>
                    </div>
                  ))}
          </div>
        </div>
      )}

      {/* Disease Detection */}
      {page === "disease" && (
        <div>
          <h2>Disease Detection</h2>
          <div className="result-container"></div>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <br /><br />
          <input
            type="text"
            placeholder="Enter your city"
            value={diseaseCity}
            onChange={(e) =>
              setDiseaseCity(e.target.value)
            }
          />
          <br /><br />

          <button onClick={handleUpload}>
            Upload
          </button>

          {result &&
            result.report && (
              <div>
                <h3>
                  Disease:{" "}
                  {
                    result.report.disease
                  }
                </h3>

                <p>
                  Confidence:{" "}
                  {
                    result.report.confidence
                  }%
                </p>
                <h3>Weather</h3>
                <p>City: {result.report.weather.city}</p>
                <p>Temperature: {result.report.weather.temperature}°C</p>
                <p>Humidity: {result.report.weather.humidity}%</p>
                <p>Condition: {result.report.weather.condition}</p>

                <h3>Medicine</h3>
                <p>
                  {
                    result.report.medicine
                  }
                </p>
                <h3>Estimated Cost</h3>
                <p>{result.report.estimated_cost}</p>

                <h3>AI Recommendation</h3>

                {typeof result.report.analysis === 'object' ? (
                  <>
                    <p>
                      <b>Cause:</b>{" "}
                      {result.report.analysis.cause}
                    </p>

                    <p>
                      <b>Severity:</b>{" "}
                      {result.report.analysis.severity}
                    </p>

                    <p>
                      <b>Weather Risk:</b>{" "}
                      {result.report.analysis.weather_risk}
                    </p>

                    <p>
                      <b>Medicine Usage:</b>{" "}
                      {result.report.analysis.medicine_usage}
                    </p>

                    <p>
                      <b>Recommendation:</b>{" "}
                      {result.report.analysis.recommendation}
                    </p>

                    <b>Precautions:</b>

                    <ul>
                      {result.report.analysis.precautions?.map(
                        (item, index) => (
                          <li key={index}>{item}</li>
                        )
                      )}
                    </ul>
                  </>
                ) : (
                  <pre
                    style={{
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {result.report.analysis}
                  </pre>
                )}
              </div>
            )}
        </div>
      )}

      {page === "price" && (
        <div className="price-page">

          <h2>Price Prediction & Market Trend</h2>

          {/* Crop Search */}
          <input
            type="text"
            placeholder="Search crop..."
            value={crop}
            onChange={(e) => {
              setCrop(e.target.value);
              setMarket("");
              setDistrict("");
              setMarketOptions([]);
              setPriceResult(null);
            }}
          />

          <button onClick={searchMarkets}>
            Search
          </button>


          {/* Market Results */}
          {marketOptions.length > 0 && (
            <div className="market-results">

              <input
                type="text"
                placeholder="Search district or market..."
                value={marketSearch}
                onChange={(e) => setMarketSearch(e.target.value)}
              />

              {/* Today's price markets */}
              {marketOptions.filter(
                (item) =>
                  item.current_price_available &&
                  `${item.district} ${item.market}`
                    .toLowerCase()
                    .includes(marketSearch.toLowerCase())
              ).length > 0 && (
                  <>
                    <h4 className="market-section-title today-title">
                      Today's Price Available
                    </h4>

                    <div className="market-list">
                      {marketOptions
                        .filter(
                          (item) =>
                            item.current_price_available &&
                            `${item.district} ${item.market}`
                              .toLowerCase()
                              .includes(marketSearch.toLowerCase())
                        )
                        .map((item, index) => (
                          <div
                            key={`today-${index}`}
                            className="market-option today-market"
                            onClick={() => {
                              setMarket(item.market);
                              setDistrict(item.district);
                              setMarketOptions([]);
                              setMarketSearch("");
                            }}
                          >
                            <div className="market-name">
                              {item.market}
                            </div>

                            <div className="market-district">
                              {item.district}
                            </div>

                            <div className="market-price">
                              ₹{item.current_price} / quintal
                            </div>

                            <div className="market-date">
                              {item.date}
                            </div>
                          </div>
                        ))}
                    </div>
                  </>
                )}

              {/* Latest available price markets */}
              {marketOptions.filter(
                (item) =>
                  !item.current_price_available &&
                  `${item.district} ${item.market}`
                    .toLowerCase()
                    .includes(marketSearch.toLowerCase())
              ).length > 0 && (
                  <>
                    <h4 className="market-section-title latest-title">
                      Latest Available Price
                    </h4>

                    <div className="market-list">
                      {marketOptions
                        .filter(
                          (item) =>
                            !item.current_price_available &&
                            `${item.district} ${item.market}`
                              .toLowerCase()
                              .includes(marketSearch.toLowerCase())
                        )
                        .map((item, index) => (
                          <div
                            key={`latest-${index}`}
                            className="market-option latest-market"
                            onClick={() => {
                              setMarket(item.market);
                              setDistrict(item.district);
                              setMarketOptions([]);
                              setMarketSearch("");
                            }}
                          >
                            <div className="market-name">
                              {item.market}
                            </div>

                            <div className="market-district">
                              {item.district}
                            </div>

                            <div className="market-price">
                              ₹{item.latest_price} / quintal
                            </div>

                            <div className="market-date">
                              {item.latest_price_date}
                            </div>
                          </div>
                        ))}
                    </div>
                  </>
                )}

            </div>
          )}


          {/* Selected Market */}
          {market && (
            <div className="selected-market">

              <p>
                Selected Market:
                <strong> {market}</strong>
              </p>

              <p>
                District:
                <strong> {district}</strong>
              </p>

            </div>
          )}


          {/* Prediction Button */}
          <button
            onClick={predictPrice}
            disabled={!crop || !market || !district}
          >
            Get Price & Prediction
          </button>


          {/* Result */}
          {priceResult && !priceResult.error && (
            <div className="result-card">

              <h3>{priceResult.crop}</h3>

              <p>
                District: {priceResult.district}
              </p>

              <p>
                Market: {priceResult.market}
              </p>

              {/* Current price available */}
              {priceResult.current_price_available ? (
                <>
                  <p>
                    Current Price: ₹{priceResult.current_price}
                  </p>

                  <p>
                    Date: {priceResult.date}
                  </p>

                  <p>
                    Minimum Price: ₹{priceResult.min_price}
                  </p>

                  <p>
                    Maximum Price: ₹{priceResult.max_price}
                  </p>
                </>
              ) : (
                <>
                  {/* Current price unavailable */}
                  <p>
                    Today's current market price is not available.
                  </p>

                  <p>
                    Latest Available Price: ₹{priceResult.latest_price}
                  </p>

                  <p>
                    Latest Price Date: {priceResult.latest_price_date}
                  </p>
                </>
              )}

              <hr />

              <p>
                Predicted Price: ₹{priceResult.predicted_price}
              </p>

              <p>
                Prediction Period: {priceResult.prediction_period}
              </p>

              <p>
                Trend: {priceResult.trend}
              </p>

              <p>
                {priceResult.recommendation}
              </p>

            </div>
          )}


          {/* Error */}
          {priceResult?.error && (
            <p className="error-message">
              {priceResult.error}
            </p>
          )}

        </div>
      )}

      {/* Weather */}
      {page === "weather" && (
        <div>
          <h2>Weather Advisory</h2>
          <div className="result-card"></div>
          <input
            type="text"
            placeholder="Enter city name"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          />

          <button onClick={getWeather}>
            Get Weather
          </button>

          {weatherResult &&
            !weatherResult.error && (
              <div>
                <h3><strong>City:</strong> {weatherResult.city}</h3>
                <p><strong>Temperature:</strong> {weatherResult.temperature}°C</p>
                <p><strong>Humidity:</strong> {weatherResult.humidity}%</p>
                <p><strong>Condition:</strong> {weatherResult.condition}</p>
                <p><strong>Advice:</strong> {weatherResult.advice}</p>
              </div>
            )}
          {weatherResult?.error && (
            <p>{weatherResult.error}</p>
          )}
        </div>
      )}

      {/* Marketplace */}
      {page === "marketplace" && (
        <div className="marketplace-page">

          <div className="marketplace-header">
            <div>
              <h2>Equipment Marketplace</h2>
              <p>Rent agricultural equipment from nearby owners.</p>
            </div>

            <button
              className="add-equipment-btn"
              onClick={() => setShowAddEquipment(!showAddEquipment)}
            >
              {showAddEquipment ? "Close" : "+ Add Equipment"}
            </button>
          </div>


          {/* ADD EQUIPMENT */}

          {showAddEquipment && (
            <div className="equipment-form-card">

              <h3>List Your Equipment</h3>

              <input
                placeholder="Equipment Name *"
                value={equipmentName}
                onChange={(e) => setEquipmentName(e.target.value)}
              />

              <select
                value={equipmentCategory}
                onChange={(e) => setEquipmentCategory(e.target.value)}
              >
                <option value="">Select Category</option>
                <option value="Tractor">Tractor</option>
                <option value="Harvester">Harvester</option>
                <option value="Rotavator">Rotavator</option>
                <option value="Cultivator">Cultivator</option>
                <option value="Seeder">Seeder</option>
                <option value="Sprayer">Sprayer</option>
                <option value="Trailer">Trailer</option>
                <option value="Other">Other</option>
              </select>

              <input
                placeholder="Owner Name *"
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
              />

              <input
                placeholder="Location *"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />

              <input
                type="number"
                placeholder="Price Per Day ₹ *"
                value={pricePerDay}
                onChange={(e) => setPricePerDay(e.target.value)}
              />

              <input
                placeholder="Contact Number *"
                value={contactNumber}
                onChange={(e) => setContactNumber(e.target.value)}
              />

              <input
                placeholder="Equipment Image URL"
                value={equipmentImage}
                onChange={(e) => setEquipmentImage(e.target.value)}
              />

              <textarea
                placeholder="Equipment description"
                value={equipmentDescription}
                onChange={(e) => setEquipmentDescription(e.target.value)}
                rows="4"
              />

              <button onClick={addEquipment}>
                List Equipment
              </button>

            </div>
          )}


          {/* SEARCH + FILTER */}

          <div className="marketplace-controls">

            <input
              type="text"
              placeholder=" Search equipment, owner or location..."
              value={marketplaceSearch}
              onChange={(e) => setMarketplaceSearch(e.target.value)}
            />

            <select
              value={marketplaceCategory}
              onChange={(e) => setMarketplaceCategory(e.target.value)}
            >
              <option value="All">All Categories</option>
              <option value="Tractor">Tractor</option>
              <option value="Harvester">Harvester</option>
              <option value="Rotavator">Rotavator</option>
              <option value="Cultivator">Cultivator</option>
              <option value="Seeder">Seeder</option>
              <option value="Sprayer">Sprayer</option>
              <option value="Trailer">Trailer</option>
              <option value="Other">Other</option>
            </select>

          </div>


          {/* EQUIPMENT CARDS */}

          <div className="equipment-grid">

            {equipment
              .filter((item) => {

                const search = marketplaceSearch.toLowerCase();

                const matchesSearch =
                  !search ||
                  item.equipment_name?.toLowerCase().includes(search) ||
                  item.owner_name?.toLowerCase().includes(search) ||
                  item.location?.toLowerCase().includes(search) ||
                  item.category?.toLowerCase().includes(search);

                const matchesCategory =
                  marketplaceCategory === "All" ||
                  item.category === marketplaceCategory;

                return matchesSearch && matchesCategory;
              })
              .map((item) => (

                <div
                  key={item.id}
                  className="equipment-card"
                >

                  <div className="equipment-image">

                    {item.image_url ? (
                      <img
                        src={item.image_url}
                        alt={item.equipment_name}
                      />
                    ) : (
                      <div className="equipment-placeholder">
                        🚜
                      </div>
                    )}

                    <span
                      className={
                        item.availability === "Available"
                          ? "equipment-status available"
                          : "equipment-status rented"
                      }
                    >
                      {item.availability}
                    </span>

                  </div>


                  <div className="equipment-card-body">

                    <span className="equipment-category">
                      {item.category || "Other"}
                    </span>

                    <h3>{item.equipment_name}</h3>

                    {item.description && (
                      <p className="equipment-description">
                        {item.description}
                      </p>
                    )}

                    <div className="equipment-info">
                      <p>👤 {item.owner_name}</p>
                      <p>📍 {item.location}</p>
                    </div>

                    <div className="equipment-price">
                      <strong>₹{item.price_per_day}</strong>
                      <span>/ day</span>
                    </div>


                    {item.availability === "Available" && (
                      <button
                        className="rent-btn"
                        onClick={() => {
                          setSelectedEquipment(item);
                          setRenterName("");
                          setRenterPhone("");
                          setRentalStartDate("");
                          setRentalEndDate("");
                        }}
                      >
                        Rent Equipment
                      </button>
                    )}

                  </div>

                </div>

              ))}

          </div>
        </div>
      )}


      {/* RENTAL MODAL */}

      {selectedEquipment && (
        <div className="rental-overlay">

          <div className="rental-modal">

            {/* HEADER */}

            <div className="modal-header">

              <button
                type="button"
                className="modal-back-btn"
                onClick={() => {
                  if (showCheckout) {
                    setShowCheckout(false);
                  } else {
                    setSelectedEquipment(null);
                  }
                }}
              >
                ← Back
              </button>

              <button
                type="button"
                className="modal-close"
                onClick={() => {
                  setSelectedEquipment(null);
                  setShowCheckout(false);
                }}
              >
                ×
              </button>

            </div>


            {/* ============================= */}
            {/* RENTAL DETAILS */}
            {/* ============================= */}

            {!showCheckout && (
              <>

                <h2>Rent Equipment</h2>

                <div className="checkout-equipment-preview">

                  {selectedEquipment.image_url ? (
                    <img
                      src={selectedEquipment.image_url}
                      alt={selectedEquipment.equipment_name}
                    />
                  ) : (
                    <div className="checkout-equipment-placeholder">
                      🚜
                    </div>
                  )}

                  <div>
                    <h3>
                      {selectedEquipment.equipment_name}
                    </h3>

                    <p>
                      📍 {selectedEquipment.location}
                    </p>

                    <strong>
                      ₹{selectedEquipment.price_per_day} / day
                    </strong>
                  </div>

                </div>


                {/* RENTER INFORMATION */}

                <div className="rental-section">

                  <h3>Renter Information</h3>

                  <input
                    type="text"
                    placeholder="Your Name *"
                    value={renterName}
                    onChange={(e) =>
                      setRenterName(e.target.value)
                    }
                  />

                  <input
                    type="tel"
                    placeholder="Your Phone Number *"
                    value={renterPhone}
                    onChange={(e) =>
                      setRenterPhone(e.target.value)
                    }
                  />

                </div>


                {/* RENTAL DATES */}

                <div className="rental-section">

                  <h3>Rental Period</h3>

                  <label>Start Date</label>

                  <input
                    type="date"
                    value={rentalStartDate}
                    min={new Date().toISOString().split("T")[0]}
                    onChange={(e) =>
                      setRentalStartDate(e.target.value)
                    }
                  />

                  <label>End Date</label>

                  <input
                    type="date"
                    value={rentalEndDate}
                    min={
                      rentalStartDate ||
                      new Date().toISOString().split("T")[0]
                    }
                    onChange={(e) =>
                      setRentalEndDate(e.target.value)
                    }
                  />

                </div>


                {/* BOOKING SUMMARY */}

                {rentalDays > 0 && (
                  <div className="rental-summary">

                    <h3>Booking Summary</h3>

                    <div className="summary-row">
                      <span>Equipment</span>

                      <strong>
                        {selectedEquipment.equipment_name}
                      </strong>
                    </div>

                    <div className="summary-row">
                      <span>Price per day</span>

                      <strong>
                        ₹{selectedEquipment.price_per_day}
                      </strong>
                    </div>

                    <div className="summary-row">
                      <span>Rental days</span>

                      <strong>
                        {rentalDays} day
                        {rentalDays > 1 ? "s" : ""}
                      </strong>
                    </div>

                    <div className="summary-row total-row">
                      <span>Total Amount</span>

                      <strong>
                        ₹{rentalTotal.toLocaleString("en-IN")}
                      </strong>
                    </div>

                  </div>
                )}


                {/* CONTINUE TO CHECKOUT */}

                <button
                  type="button"
                  className="confirm-rental-btn"
                  onClick={() => {

                    if (!renterName.trim()) {
                      alert("Please enter your name");
                      return;
                    }

                    if (!renterPhone.trim()) {
                      alert("Please enter your phone number");
                      return;
                    }

                    if (!rentalStartDate || !rentalEndDate) {
                      alert("Please select rental dates");
                      return;
                    }

                    if (rentalDays <= 0) {
                      alert("Please select a valid rental period");
                      return;
                    }

                    setShowCheckout(true);

                  }}
                >
                  Continue to Checkout
                </button>

              </>
            )}


            {/* ============================= */}
            {/* CHECKOUT */}
            {/* ============================= */}

            {showCheckout && (
              <>

                <h2>Review & Checkout</h2>

                <div className="checkout-card">

                  <div className="checkout-title">
                    <h3>
                      {selectedEquipment.equipment_name}
                    </h3>

                    <span className="checkout-location">
                      📍 {selectedEquipment.location}
                    </span>
                  </div>


                  {/* RENTER */}

                  <div className="checkout-section">

                    <h4>Renter</h4>

                    <p>
                      👤 {renterName}
                    </p>

                    <p>
                      📞 {renterPhone}
                    </p>

                  </div>


                  {/* OWNER */}

                  <div className="checkout-section">

                    <h4>Equipment Owner</h4>

                    <p>
                      👤 {selectedEquipment.owner_name}
                    </p>

                    <p>
                      📍 {selectedEquipment.location}
                    </p>
                    <p>
                      📞 {selectedEquipment.contact_number}

                    </p>

                  </div>


                  {/* DATES */}

                  <div className="checkout-section">

                    <h4>Rental Period</h4>

                    <p>
                      📅 {rentalStartDate}
                    </p>

                    <p>
                      📅 {rentalEndDate}
                    </p>

                    <p>
                      {rentalDays} day
                      {rentalDays > 1 ? "s" : ""}
                    </p>

                  </div>


                  {/* PAYMENT SUMMARY */}

                  <div className="payment-summary">

                    <div className="summary-row">
                      <span>Price per day</span>

                      <strong>
                        ₹{selectedEquipment.price_per_day}
                      </strong>
                    </div>

                    <div className="summary-row">
                      <span>
                        {rentalDays} × daily rate
                      </span>

                      <strong>
                        ₹{rentalTotal.toLocaleString("en-IN")}
                      </strong>
                    </div>

                    <div className="summary-row total-row">
                      <span>Total to Pay</span>

                      <strong>
                        ₹{rentalTotal.toLocaleString("en-IN")}
                      </strong>
                    </div>

                  </div>


                  {/* PAYMENT BUTTON */}

                  <button
                    type="button"
                    className="payment-btn"
                    onClick={rentEquipment}
                  >
                    💳 Proceed to Payment
                  </button>


                  <p className="secure-payment-note">
                    🔒 Secure payment
                  </p>

                </div>

              </>
            )}

          </div>

        </div>
      )}
      {/* History */}
      {page === "history" && (
        <div>
          <h2>Prediction History</h2>

          <button onClick={fetchHistory}>
            Show History
          </button>

          <button
            onClick={clearHistory}
            style={{
              marginLeft: "10px",
            }}
          >
            Clear History
          </button>

          {history.length > 0 && (
            <div>
              {history.map((item) => (
                <div
                  key={item.id}
                  className="history-card"
                >
                  <p>
                    {item.disease}
                  </p>

                  <p>
                    {item.confidence}
                  </p>

                  <p>
                    {item.treatment}
                  </p>

                  <hr />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {page === "assistant" && (
        <div className="chat-page">

          <h2>AI Agriculture Assistant</h2>
          <button
            onClick={() => setChatMessages([])}
            style={{ marginBottom: "15px" }}
          >
            Clear Chat
          </button>

          <div className="chat-box">
            <div ref={chatEndRef}></div>

            {chatMessages.length === 0 && (
              <div className="welcome-chat">
                <h2>AgriPulse AI</h2>
                <p>
                  Ask anything about your crop,
                  disease,weather,price or equipment.
                </p>
              </div>
            )}
            {chatMessages.map((msg, index) => (
              <div
                key={index}
                className={
                  msg.sender === "user"
                    ? "chat-row user-row"
                    : "chat-row ai-row"
                }
              >
                <div
                  className={
                    msg.sender === "user"
                      ? "user-message"
                      : "ai-message"
                  }
                >

                </div>
                {msg.text}
              </div>
            ))}



            {loadingChat && (
              <div className="ai-message">
                <span></span>
                <span></span>
                <span></span>
              </div>
            )}

          </div>

          <div className="chat-input-area">

            <input
              value={chatInput}
              onChange={(e) =>
                setChatInput(e.target.value)
              }
              placeholder="Ask anything about your crop..."
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  sendMessage();
                }
              }}
            />

            <button onClick={sendMessage}>
              Send
            </button>

          </div>

        </div>
      )}

      <footer className="footer">
        <h3>AgriPulse</h3>
        <p>
          AI-Powered Smart Agriculture Platform
        </p>
        <p>
          Disease Detection | Weather Advisory | Price Prediction | Equipment Rental
        </p>
        <p>
          &copy; 2026 AgriPulse. All rights reserved.
        </p>
      </footer>
      <div
        className="ai-floating-button"
        onClick={() => setPage("assistant")}
      >
        🤖
      </div>
    </div>
  );
}

export default App;