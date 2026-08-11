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
      console.log("price result:",data);

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
    await fetch(
      `http://127.0.0.1:8000/equipment?equipment_name=${equipmentName}&owner_name=${ownerName}&price_per_day=${pricePerDay}&location=${location}&contact_number=${contactNumber}`,
      {
        method: "POST",
      }
    );
    alert("Equipment added successfully!");
    fetchEquipment();
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

  const rentEquipment = async (id) => {
    await fetch(
      `http://127.0.0.1:8000/rent-equipment?equipment_id=${id}&renter_name=Farmer&renter_phone=9876543210`,
      {
        method: "POST",
      }
    );

    fetchEquipment();
  };

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
        <div>
          <h2>
            Equipment Marketplace
          </h2>
          <h3>Add Equipment</h3>

          <input
            placeholder="Equipment Name"
            value={equipmentName}
            onChange={(e) =>
              setEquipmentName(e.target.value)
            }
          />
          <br /><br />

          <input
            placeholder="Owner Name"
            value={ownerName}
            onChange={(e) =>
              setOwnerName(e.target.value)
            }
          />
          <br /><br />

          <input
            placeholder="Location"
            value={location}
            onChange={(e) =>
              setLocation(e.target.value)
            }
          />
          <br /><br />

          <input
            placeholder="Price Per Day"
            value={pricePerDay}
            onChange={(e) =>
              setPricePerDay(e.target.value)
            }
          />
          <br /><br />

          <input
            placeholder="Contact Number"
            value={contactNumber}
            onChange={(e) =>
              setContactNumber(e.target.value)
            }
          />
          <br /><br />

          <button onClick={addEquipment}>
            Add Equipment
          </button>
          <hr />

          <button onClick={fetchEquipment}>
            Load Equipment
          </button>

          {equipment.map((item) => (
            <div
              key={item.id}
              className="market-card"
            >
              <h4>
                {item.equipment_name}
              </h4>

              <p>
                Owner: {item.owner_name}
              </p>

              <p>
                Location: {item.location}
              </p>

              <p>
                ₹{item.price_per_day}/day
              </p>

              <p>
                Status: {item.availability}
              </p>

              {item.availability ===
                "Available" && (
                  <button
                    onClick={() =>
                      rentEquipment(item.id)
                    }
                  >
                    Rent
                  </button>
                )}
            </div>
          ))}
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