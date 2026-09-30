import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { API_URL, VoiceMic } from "../voice";
import { notify } from "../ui/notify";
import TrackingPanel from "../TrackingPanel";
import {
  Button,
  Chip,
  EmptyState,
  Input,
  Modal,
  ModalHead,
  PageHeader,
  Pill,
  Reveal,
  Segmented,
  Select,
  Skeleton,
  TextArea,
} from "../ui/kit";
import { EmptyArt } from "../ui/art";
import {
  Calendar,
  Clock,
  CreditCard,
  Lock,
  MapPin,
  Navigation,
  Phone,
  Plus,
  Radio,
  Search,
  Tractor,
  User,
} from "../ui/icons";
import { CATEGORIES, categoryClass, categoryIcon } from "./marketplaceParts";

const today = () => new Date().toISOString().split("T")[0];

const blankEquipment = (user) => ({
  name: "",
  category: "",
  owner: (user && user.name) || "",
  location: "",
  perDay: "",
  perHour: "",
  contact: (user && user.phone) || "",
  image: "",
  description: "",
});

export default function MarketplacePage({ token, user, lang, t, jsonHeaders, sessionExpired, goLogin }) {
  const [equipment, setEquipment] = useState(null);
  const [myRentals, setMyRentals] = useState([]);

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [nearMe, setNearMe] = useState(null);
  const [radiusKm, setRadiusKm] = useState(10);

  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState(() => blankEquipment(user));
  const [addCoords, setAddCoords] = useState(null);
  const [adding, setAdding] = useState(false);

  const [selected, setSelected] = useState(null);
  const [showCheckout, setShowCheckout] = useState(false);
  const [paying, setPaying] = useState(false);
  const [renterName, setRenterName] = useState("");
  const [renterPhone, setRenterPhone] = useState("");
  const [bookingType, setBookingType] = useState("day");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [bookedSlots, setBookedSlots] = useState([]);

  const setAdd = (key, value) => setAddForm((old) => ({ ...old, [key]: value }));

  const getPosition = (onFound) => {
    if (!navigator.geolocation) {
      notify("Location is not supported by this browser", "error");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => onFound({ lat: position.coords.latitude, lng: position.coords.longitude }),
      () => notify("Could not get your location. Please allow location access.", "error"),
      { enableHighAccuracy: true, timeout: 15000 }
    );
  };

  // ------------------------------------------------------------------ data
  const fetchEquipment = async () => {
    try {
      const query = nearMe ? `?lat=${nearMe.lat}&lng=${nearMe.lng}&radius_km=${radiusKm}` : "";
      const res = await fetch(`${API_URL}/equipment${query}`);

      if (res.ok) setEquipment(await res.json());
      else setEquipment((old) => old || []);
    } catch (error) {
      console.warn("Backend not reachable:", error.message);
      setEquipment((old) => old || []);
    }
  };

  const fetchMyRentals = async () => {
    if (!token) return;

    try {
      const res = await fetch(`${API_URL}/rentals`, { headers: jsonHeaders() });

      if (res.status === 401) {
        sessionExpired();
        return;
      }

      const data = await res.json();

      setMyRentals(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error(error);
    }
  };

  const loadBookedSlots = async (equipmentId) => {
    try {
      const res = await fetch(`${API_URL}/equipment/${equipmentId}/bookings`);

      setBookedSlots(res.ok ? await res.json() : []);
    } catch (error) {
      setBookedSlots([]);
    }
  };

  useEffect(() => {
    fetchEquipment();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nearMe, radiusKm]);

  useEffect(() => {
    fetchMyRentals();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // ------------------------------------------------------------- add machine
  const addEquipment = async () => {
    if (!addForm.name.trim() || !addForm.owner.trim() || !addForm.location.trim() || !addForm.perDay || !addForm.contact.trim()) {
      notify("Please fill all required fields", "error");
      return;
    }

    setAdding(true);

    try {
      const res = await fetch(`${API_URL}/equipment`, {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify({
          equipment_name: addForm.name,
          owner_name: addForm.owner,
          price_per_day: Number(addForm.perDay),
          price_per_hour: addForm.perHour ? Number(addForm.perHour) : null,
          latitude: addCoords ? addCoords.lat : null,
          longitude: addCoords ? addCoords.lng : null,
          location: addForm.location,
          contact_number: addForm.contact,
          category: addForm.category || "Other",
          description: addForm.description,
          image_url: addForm.image,
        }),
      });

      if (res.status === 401) {
        sessionExpired();
        return;
      }

      const data = await res.json();

      if (!res.ok) {
        notify(typeof data.detail === "string" ? data.detail : "Failed to add equipment", "error");
        return;
      }

      notify("Equipment added successfully!", "success");

      setAddForm(blankEquipment(user));
      setAddCoords(null);
      setShowAdd(false);
      fetchEquipment();
    } catch (error) {
      console.error(error);
      notify("Failed to add equipment", "error");
    } finally {
      setAdding(false);
    }
  };

  // ------------------------------------------------------------ rental maths
  const isHourly = bookingType === "hour";

  const rentalDays = (() => {
    if (!startDate || !endDate) return 0;

    const difference = (new Date(endDate) - new Date(startDate)) / (1000 * 60 * 60 * 24);

    return difference >= 0 ? difference + 1 : 0;
  })();

  const rentalHours = (() => {
    if (!startTime || !endTime) return 0;

    const difference = (new Date(endTime) - new Date(startTime)) / (1000 * 60 * 60);

    return difference > 0 ? Math.ceil(difference) : 0;
  })();

  const rentalUnits = isHourly ? rentalHours : rentalDays;
  const unitName = isHourly ? "hour" : "day";

  const rentalRate = selected ? Number(isHourly ? selected.price_per_hour : selected.price_per_day) : 0;
  const rentalTotal = rentalUnits > 0 && selected ? rentalUnits * rentalRate : 0;

  const openRental = (item) => {
    setSelected(item);
    setShowCheckout(false);
    setRenterName((user && user.name) || "");
    setRenterPhone((user && user.phone) || "");
    setStartDate("");
    setEndDate("");
    setBookingType("day");
    setStartTime("");
    setEndTime("");
    loadBookedSlots(item.id);
  };

  const closeRental = () => {
    setSelected(null);
    setShowCheckout(false);
  };

  const continueToCheckout = () => {
    if (!renterName.trim()) return notify("Please enter your name", "error");
    if (!renterPhone.trim()) return notify("Please enter your phone number", "error");
    if (isHourly ? !startTime || !endTime : !startDate || !endDate) return notify("Please select the rental period", "error");
    if (rentalUnits <= 0) return notify("Please select a valid rental period", "error");

    setShowCheckout(true);
  };

  // ---------------------------------------------------------------- payment
  const rentEquipment = async () => {
    if (!selected) return;

    if (!token) {
      notify("Please login to rent equipment", "error");
      goLogin();
      return;
    }

    setPaying(true);

    try {
      // 1. create the rental
      const rentalResponse = await fetch(`${API_URL}/rent-equipment`, {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify({
          equipment_id: selected.id,
          renter_name: renterName,
          renter_phone: renterPhone,
          booking_type: bookingType,
          ...(isHourly ? { start_at: startTime, end_at: endTime } : { start_date: startDate, end_date: endDate }),
        }),
      });

      if (rentalResponse.status === 401) {
        sessionExpired();
        return;
      }

      const rentalData = await rentalResponse.json();

      if (!rentalResponse.ok) {
        notify(typeof rentalData.detail === "string" ? rentalData.detail : "Failed to create rental", "error");
        return;
      }

      // 2. create the Razorpay order
      const paymentResponse = await fetch(`${API_URL}/create-payment-order`, {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify({ rental_id: rentalData.rental_id }),
      });

      const paymentData = await paymentResponse.json();

      if (!paymentResponse.ok) {
        notify(typeof paymentData.detail === "string" ? paymentData.detail : "Failed to create payment order", "error");
        return;
      }

      // 3. open Razorpay checkout
      if (!window.Razorpay) {
        notify("Razorpay Checkout failed to load. Please refresh the page.", "error");
        return;
      }

      const options = {
        key: paymentData.key_id,
        amount: paymentData.amount,
        currency: paymentData.currency,
        name: "AgriPulse",
        description: `Equipment Rental - ${selected.equipment_name}`,
        order_id: paymentData.order_id,
        prefill: { name: renterName, contact: renterPhone },
        notes: { rental_id: String(rentalData.rental_id), equipment: selected.equipment_name },
        theme: { color: "#0f9d58" },

        // UPI first: most farmers pay with GPay / PhonePe / Paytm
        config: {
          display: {
            blocks: { upi: { name: "Pay using UPI", instruments: [{ method: "upi" }] } },
            sequence: ["block.upi"],
            preferences: { show_default_blocks: !paymentData.upi_only },
          },
        },

        handler: async function (response) {
          // 4. verify the payment on the server
          try {
            const verifyResponse = await fetch(`${API_URL}/verify-payment`, {
              method: "POST",
              headers: jsonHeaders(),
              body: JSON.stringify({
                rental_id: rentalData.rental_id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              }),
            });

            const verifyData = await verifyResponse.json();

            if (!verifyResponse.ok) {
              notify(verifyData.detail || "Payment verification failed", "error");
              return;
            }

            notify(
              `Payment successful!\n${selected.equipment_name} · Rental #${rentalData.rental_id} · ₹${rentalData.total_amount} paid. Your rental is confirmed.`,
              "success"
            );

            closeRental();
            fetchEquipment();
            fetchMyRentals();
          } catch (error) {
            console.error("Payment verification error:", error);
            notify("Payment was completed, but verification failed. Please contact the administrator.", "error");
          }
        },

        modal: { ondismiss: () => console.log("Razorpay checkout closed by user") },
      };

      const razorpay = new window.Razorpay(options);

      razorpay.on("payment.failed", (response) => {
        console.error("Payment failed:", response.error);
        notify(response.error.description || "Payment failed. Please try again.", "error");
      });

      razorpay.open();
    } catch (error) {
      console.error("Rental/payment error:", error);
      notify("Something went wrong while processing the rental.", "error");
    } finally {
      setPaying(false);
    }
  };

  // ---------------------------------------------------------------- render
  const query = search.toLowerCase();

  const visible = (equipment || []).filter((item) => {
    const matchesSearch =
      !query ||
      item.equipment_name?.toLowerCase().includes(query) ||
      item.owner_name?.toLowerCase().includes(query) ||
      item.location?.toLowerCase().includes(query) ||
      item.category?.toLowerCase().includes(query);

    return matchesSearch && (category === "All" || item.category === category);
  });

  return (
    <div className="page">
      <PageHeader
        icon={Tractor}
        tone="forest"
        title={t("title_marketplace")}
        subtitle="Rent agricultural equipment from nearby owners."
        actions={
          <Button icon={Plus} onClick={() => setShowAdd(true)}>
            {String(t("btn_list_equipment")).replace(/^\+\s*/, "")}
          </Button>
        }
      />

      {user && user.role === "owner" && (
        <TrackingPanel apiUrl={API_URL} token={token} user={user} onChanged={fetchEquipment} />
      )}

      {/* ---------------------------------------------------------- my rentals */}
      {user && myRentals.length > 0 && (
        <Reveal className="card">
          <h3 className="card-title">
            <Calendar size={20} /> My rentals &amp; bookings
          </h3>

          <div className="rental-list">
            {myRentals.map((rental) => (
              <div key={rental.id} className="rental-row">
                <span className="rental-id">#{rental.id}</span>

                <span className="rental-what">
                  Equipment {rental.equipment_id}
                  <small>
                    {rental.start_date} → {rental.end_date}
                  </small>
                </span>

                <strong>₹{rental.total_amount}</strong>

                <span
                  className={`rental-status status-${String(rental.status).toLowerCase().replace(/\s+/g, "-")}`}
                >
                  {rental.status}
                  {rental.payment_status === "Paid" ? " · Paid" : ""}
                </span>
              </div>
            ))}
          </div>
        </Reveal>
      )}

      {/* ------------------------------------------------------------ filters */}
      <div className="card filter-card">
        <div className="search-row">
          <Input
            id="market-search"
            className="grow"
            icon={Search}
            placeholder="Search equipment, owner or location..."
            aria-label="Search equipment"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <VoiceMic lang={lang} t={t} onText={(text) => setSearch(text)} />

          <Button
            variant={nearMe ? "primary" : "ghost"}
            icon={Navigation}
            onClick={() => (nearMe ? setNearMe(null) : getPosition(setNearMe))}
          >
            {nearMe ? `${radiusKm} km · Clear` : t("btn_near_me")}
          </Button>
        </div>

        <AnimatePresence>
          {nearMe && (
            <motion.div
              className="radius-row"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
            >
              <span className="note">Search radius</span>

              <Segmented
                ariaLabel="radius"
                value={radiusKm}
                onChange={setRadiusKm}
                options={[5, 10, 25, 50].map((km) => [km, `${km} km`])}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <div className="chip-scroll" role="group" aria-label="Category">
          {["All", ...CATEGORIES].map((name) => (
            <Chip key={name} active={category === name} onClick={() => setCategory(name)}>
              {name === "All" ? "All Categories" : name}
            </Chip>
          ))}
        </div>
      </div>

      {/* --------------------------------------------------------------- grid */}
      {equipment === null ? (
        <div className="equipment-grid">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} height={320} radius={24} />
          ))}
        </div>
      ) : visible.length === 0 ? (
        <EmptyState
          art={
            <EmptyArt>
              <Tractor size={34} />
            </EmptyArt>
          }
          title={nearMe ? `No equipment within ${radiusKm} km` : "No equipment found"}
          text={
            nearMe
              ? "Try a wider radius, or clear the location filter."
              : "Try a different search, or list your own machine for others to rent."
          }
          action={
            <Button icon={Plus} onClick={() => setShowAdd(true)}>
              List equipment
            </Button>
          }
        />
      ) : (
        <div className="equipment-grid">
          {visible.map((item, index) => {
            const Icon = categoryIcon(item.category);
            const available = item.availability === "Available";

            return (
              <Reveal key={item.id} delay={Math.min(index, 8) * 0.05} className="equipment-card">
                <div className={`equipment-media ${item.image_url ? "" : categoryClass(item.category)}`}>
                  {item.image_url ? (
                    <img src={item.image_url} alt={item.equipment_name} />
                  ) : (
                    <Icon size={64} className="media-icon" />
                  )}

                  <Pill tone={available ? "good" : "warn"} className="equipment-status">
                    {item.availability}
                  </Pill>

                  {item.location_live && (
                    <span className="live-badge">
                      <span className="live-dot" /> Live
                    </span>
                  )}
                </div>

                <div className="equipment-body">
                  <span className="equipment-category">{item.category || "Other"}</span>

                  <h3>{item.equipment_name}</h3>

                  {item.description && <p className="equipment-description">{item.description}</p>}

                  <ul className="equipment-facts">
                    <li>
                      <User size={14} /> {item.owner_name}
                    </li>

                    <li>
                      <MapPin size={14} /> {item.location}
                    </li>

                    {item.distance_km !== undefined && (
                      <li className="fact-accent">
                        <Navigation size={14} /> {item.distance_km} km away
                      </li>
                    )}

                    {item.location_geo && (
                      <li>
                        <Radio size={14} />
                        {item.location_live ? (
                          " Live location "
                        ) : (
                          <> GPS seen {(item.location_updated_at || "").slice(0, 16).replace("T", " ")} </>
                        )}
                        <a
                          href={`https://www.google.com/maps?q=${item.location_geo.lat},${item.location_geo.lng}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Map
                        </a>
                      </li>
                    )}
                  </ul>

                  <div className="equipment-foot">
                    <div className="equipment-price">
                      <strong>₹{item.price_per_day}</strong>
                      <small>/ day</small>
                      {item.price_per_hour && <span className="hourly">or ₹{item.price_per_hour} / hour</span>}
                    </div>

                    {available && (
                      <Button size="sm" onClick={() => openRental(item)}>
                        Rent Equipment
                      </Button>
                    )}
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>
      )}

      {/* --------------------------------------------------- add equipment */}
      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="List your equipment" size="md">
        <ModalHead title="List Your Equipment" subtitle="Farmers near you will be able to rent it." onClose={() => setShowAdd(false)} />

        <div className="form-grid">
          <Input id="eq-name" label="Equipment name *" placeholder="Equipment Name *" value={addForm.name} onChange={(e) => setAdd("name", e.target.value)} />

          <Select
            id="eq-category"
            label="Category"
            value={addForm.category}
            onChange={(e) => setAdd("category", e.target.value)}
          >
            <option value="">Select Category</option>
            {CATEGORIES.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </Select>

          <div className="two-col">
            <Input id="eq-owner" label="Owner name *" icon={User} placeholder="Owner Name *" value={addForm.owner} onChange={(e) => setAdd("owner", e.target.value)} />

            <Input id="eq-contact" label="Contact number *" icon={Phone} placeholder="Contact Number *" value={addForm.contact} onChange={(e) => setAdd("contact", e.target.value)} />
          </div>

          <Input id="eq-location" label="Location *" icon={MapPin} placeholder="Location *" value={addForm.location} onChange={(e) => setAdd("location", e.target.value)} />

          <div className="two-col">
            <Input id="eq-day" label="Price per day (₹) *" type="number" placeholder="Price Per Day ₹ *" value={addForm.perDay} onChange={(e) => setAdd("perDay", e.target.value)} />

            <Input
              id="eq-hour"
              label="Price per hour (₹)"
              type="number"
              placeholder="Optional, enables hourly booking"
              value={addForm.perHour}
              onChange={(e) => setAdd("perHour", e.target.value)}
            />
          </div>

          <div className="gps-box">
            <Button variant={addCoords ? "soft" : "ghost"} icon={Navigation} onClick={() => getPosition(setAddCoords)}>
              {addCoords ? "Location captured" : "Use my current location"}
            </Button>

            <span className="note">
              {addCoords
                ? `GPS set: ${addCoords.lat.toFixed(4)}, ${addCoords.lng.toFixed(4)}`
                : "Needed so nearby farmers can find your equipment"}
            </span>
          </div>

          <Input id="eq-image" label="Photo link (optional)" placeholder="Equipment Image URL" value={addForm.image} onChange={(e) => setAdd("image", e.target.value)} />

          <TextArea id="eq-desc" label="Description" placeholder="Equipment description" rows="3" value={addForm.description} onChange={(e) => setAdd("description", e.target.value)} />
        </div>

        <div className="modal-actions">
          <Button variant="ghost" onClick={() => setShowAdd(false)}>
            Cancel
          </Button>

          <Button loading={adding} icon={Plus} onClick={addEquipment}>
            List Equipment
          </Button>
        </div>
      </Modal>

      {/* ------------------------------------------------------ rent + pay */}
      <Modal open={Boolean(selected)} onClose={closeRental} title="Rent equipment" size="md">
        {selected && (
          <>
            <ModalHead
              title={showCheckout ? "Review & Checkout" : "Rent Equipment"}
              subtitle={showCheckout ? "Check everything, then pay securely." : "Choose when you need it."}
              onClose={closeRental}
              onBack={showCheckout ? () => setShowCheckout(false) : undefined}
            />

            <div className="rent-preview">
              {selected.image_url ? (
                <img src={selected.image_url} alt={selected.equipment_name} />
              ) : (
                <span className={`rent-icon ${categoryClass(selected.category)}`}>
                  {(() => {
                    const Icon = categoryIcon(selected.category);

                    return <Icon size={30} />;
                  })()}
                </span>
              )}

              <div>
                <h3>{selected.equipment_name}</h3>

                <p className="note">
                  <MapPin size={13} /> {selected.location}
                </p>

                <strong className="rent-rate">₹{selected.price_per_day} / day</strong>
              </div>
            </div>

            <AnimatePresence mode="wait" initial={false}>
              {!showCheckout ? (
                <motion.div
                  key="details"
                  className="form-grid"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="two-col">
                    <Input id="rent-name" label="Your name *" icon={User} placeholder="Your Name *" value={renterName} onChange={(e) => setRenterName(e.target.value)} />

                    <Input id="rent-phone" label="Your phone *" icon={Phone} type="tel" placeholder="Your Phone Number *" value={renterPhone} onChange={(e) => setRenterPhone(e.target.value)} />
                  </div>

                  <div className="field">
                    <span className="field-label">Rental period</span>

                    {selected.price_per_hour && (
                      <Segmented
                        ariaLabel="booking"
                        value={bookingType}
                        onChange={setBookingType}
                        options={[
                          ["day", "By the day"],
                          ["hour", "By the hour"],
                        ]}
                      />
                    )}
                  </div>

                  {!isHourly ? (
                    <div className="two-col">
                      <Input
                        id="rent-start"
                        label="Start Date"
                        type="date"
                        value={startDate}
                        min={today()}
                        onChange={(e) => setStartDate(e.target.value)}
                      />

                      <Input
                        id="rent-end"
                        label="End Date"
                        type="date"
                        value={endDate}
                        min={startDate || today()}
                        onChange={(e) => setEndDate(e.target.value)}
                      />
                    </div>
                  ) : (
                    <div className="two-col">
                      <Input id="rent-start-t" label="Start time" type="datetime-local" step="900" value={startTime} onChange={(e) => setStartTime(e.target.value)} />

                      <Input id="rent-end-t" label="End time" type="datetime-local" step="900" value={endTime} min={startTime} onChange={(e) => setEndTime(e.target.value)} />
                    </div>
                  )}

                  {bookedSlots.length > 0 && (
                    <div className="booked">
                      <strong>
                        <Clock size={14} /> Already booked
                      </strong>

                      {bookedSlots.map((slot, index) => (
                        <span key={index} className="booked-slot">
                          {slot.start_at.slice(0, 16).replace("T", " ")} → {slot.end_at.slice(0, 16).replace("T", " ")}
                        </span>
                      ))}
                    </div>
                  )}

                  <AnimatePresence>
                    {rentalUnits > 0 && (
                      <motion.div
                        className="summary"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                      >
                        <h4>Booking Summary</h4>

                        <div className="summary-row">
                          <span>Equipment</span>
                          <strong>{selected.equipment_name}</strong>
                        </div>

                        <div className="summary-row">
                          <span>Price per {unitName}</span>
                          <strong>₹{rentalRate}</strong>
                        </div>

                        <div className="summary-row">
                          <span>Rental {unitName}s</span>

                          <strong>
                            {rentalUnits} {unitName}
                            {rentalUnits > 1 ? "s" : ""}
                          </strong>
                        </div>

                        <div className="summary-row total">
                          <span>Total Amount</span>
                          <strong>₹{rentalTotal.toLocaleString("en-IN")}</strong>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <Button size="lg" block onClick={continueToCheckout}>
                    Continue to Checkout
                  </Button>
                </motion.div>
              ) : (
                <motion.div
                  key="checkout"
                  className="form-grid"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="review-grid">
                    <div className="review-box">
                      <h4>Renter</h4>
                      <p>
                        <User size={14} /> {renterName}
                      </p>
                      <p>
                        <Phone size={14} /> {renterPhone}
                      </p>
                    </div>

                    <div className="review-box">
                      <h4>Equipment Owner</h4>
                      <p>
                        <User size={14} /> {selected.owner_name}
                      </p>
                      <p>
                        <MapPin size={14} /> {selected.location}
                      </p>
                      <p>
                        <Phone size={14} /> {selected.contact_number}
                      </p>
                    </div>

                    <div className="review-box wide">
                      <h4>Rental Period</h4>
                      <p>
                        <Calendar size={14} /> {isHourly ? startTime.replace("T", " ") : startDate} → {isHourly ? endTime.replace("T", " ") : endDate}
                      </p>
                      <p>
                        {rentalUnits} {unitName}
                        {rentalUnits > 1 ? "s" : ""}
                      </p>
                    </div>
                  </div>

                  <div className="summary">
                    <div className="summary-row">
                      <span>Price per {unitName}</span>
                      <strong>₹{rentalRate}</strong>
                    </div>

                    <div className="summary-row">
                      <span>
                        {rentalUnits} × {unitName}ly rate
                      </span>
                      <strong>₹{rentalTotal.toLocaleString("en-IN")}</strong>
                    </div>

                    <div className="summary-row total">
                      <span>Total to Pay</span>
                      <strong>₹{rentalTotal.toLocaleString("en-IN")}</strong>
                    </div>
                  </div>

                  <Button size="lg" block loading={paying} icon={CreditCard} onClick={rentEquipment}>
                    Proceed to Payment
                  </Button>

                  <p className="secure-note">
                    <Lock size={14} /> Secure payment
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </Modal>
    </div>
  );
}
