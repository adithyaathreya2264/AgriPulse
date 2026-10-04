import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { API_URL, VoiceMic } from "../voice";
import { enumText, serverText } from "../i18n";
import { notify, confirmDialog } from "../ui/notify";
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
  MapPin,
  Navigation,
  Phone,
  Plus,
  Trash2,
  Radio,
  Search,
  Tractor,
  User,
} from "../ui/icons";
import { CATEGORIES, categoryClass, categoryIcon, directImageUrl } from "./marketplaceParts";

// Equipment can only be booked from this many days after today (same rule as the server)
const MIN_LEAD_DAYS = 2;

// earliest bookable date, as YYYY-MM-DD in the farmer's local time
const earliestDate = () => {
  const day = new Date();

  day.setDate(day.getDate() + MIN_LEAD_DAYS);

  const pad = (n) => String(n).padStart(2, "0");

  return `${day.getFullYear()}-${pad(day.getMonth() + 1)}-${pad(day.getDate())}`;
};

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
      notify(t("common.location_is_not_supported_by_this"), "error");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => onFound({ lat: position.coords.latitude, lng: position.coords.longitude }),
      () => notify(t("common.could_not_get_your_location_please"), "error"),
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
      notify(t("market.please_fill_all_required_fields"), "error");
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
          image_url: directImageUrl(addForm.image),
        }),
      });

      if (res.status === 401) {
        sessionExpired();
        return;
      }

      const data = await res.json();

      if (!res.ok) {
        notify(typeof data.detail === "string" ? serverText(t, data.detail) : t("market.err_add"), "error");
        return;
      }

      notify(t("market.equipment_added_successfully"), "success");

      setAddForm(blankEquipment(user));
      setAddCoords(null);
      setShowAdd(false);
      fetchEquipment();
    } catch (error) {
      console.error(error);
      notify(t("market.failed_to_add_equipment"), "error");
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

  const rentalRate = selected ? Number(isHourly ? selected.price_per_hour : selected.price_per_day) : 0;
  const rentalTotal = rentalUnits > 0 && selected ? rentalUnits * rentalRate : 0;

  // "3 days" / "1 hour" in the farmer's language
  const count = (n) => t((isHourly ? "market.n_hour" : "market.n_day") + (n === 1 ? "_one" : "_other"), { n });

  const cat = (name) => enumText(t, "cat.", name);

  const openRental = (item) => {
    setSelected(item);
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
  };

  // Step 1: book. The slot is held until the start date; pay before then or the booking expires.
  const bookNow = async () => {
    if (!selected) return;

    if (!token) {
      notify(t("market.please_login_to_rent_equipment"), "error");
      goLogin();
      return;
    }

    if (!renterName.trim()) return notify(t("market.please_enter_your_name"), "error");
    if (!renterPhone.trim()) return notify(t("market.please_enter_your_phone_number"), "error");
    if (isHourly ? !startTime || !endTime : !startDate || !endDate) return notify(t("market.please_select_the_rental_period"), "error");
    if (rentalUnits <= 0) return notify(t("market.please_select_a_valid_rental_period"), "error");

    setPaying(true);

    try {
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
        notify(typeof rentalData.detail === "string" ? serverText(t, rentalData.detail) : t("market.err_rental"), "error");
        return;
      }

      notify(
        t("market.booked_pay_before", {
          equipment: selected.equipment_name,
          id: rentalData.rental_id,
          start: String(rentalData.start_at).slice(0, 16).replace("T", " "),
        }),
        "success"
      );

      closeRental();
      fetchEquipment();
      fetchMyRentals();
    } catch (error) {
      console.error("Booking error:", error);
      notify(t("market.something_went_wrong_while_processing_"), "error");
    } finally {
      setPaying(false);
    }
  };

  // ---------------------------------------------------------------- payment
  // Step 2: pay a booking (from "My rentals"), once the renter has met the owner
  const payRental = async (rentalData, equipmentName) => {
    if (!token) {
      notify(t("market.please_login_to_rent_equipment"), "error");
      goLogin();
      return;
    }

    setPaying(true);

    try {
      // 1. create the Razorpay order
      const paymentResponse = await fetch(`${API_URL}/create-payment-order`, {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify({ rental_id: rentalData.id }),
      });

      if (paymentResponse.status === 401) {
        sessionExpired();
        return;
      }

      const paymentData = await paymentResponse.json();

      if (!paymentResponse.ok) {
        notify(typeof paymentData.detail === "string" ? serverText(t, paymentData.detail) : t("market.err_order"), "error");
        fetchMyRentals();
        return;
      }

      // 2. open Razorpay checkout
      if (!window.Razorpay) {
        notify(t("market.razorpay_checkout_failed_to_load_pleas"), "error");
        return;
      }

      const options = {
        key: paymentData.key_id,
        amount: paymentData.amount,
        currency: paymentData.currency,
        name: "AgriPulse",
        description: t("market.rzp_description", { equipment: equipmentName }),
        order_id: paymentData.order_id,
        prefill: { name: rentalData.renter_name, contact: rentalData.renter_phone },
        notes: { rental_id: String(rentalData.id), equipment: equipmentName },
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
          // 3. verify the payment on the server
          try {
            const verifyResponse = await fetch(`${API_URL}/verify-payment`, {
              method: "POST",
              headers: jsonHeaders(),
              body: JSON.stringify({
                rental_id: rentalData.id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              }),
            });

            const verifyData = await verifyResponse.json();

            if (!verifyResponse.ok) {
              notify(serverText(t, verifyData.detail) || t("market.err_verify"), "error");
              return;
            }

            notify(
              t("market.payment_success", {
                equipment: equipmentName,
                id: rentalData.id,
                amount: rentalData.total_amount,
              }),
              "success"
            );

            fetchEquipment();
            fetchMyRentals();
          } catch (error) {
            console.error("Payment verification error:", error);
            notify(t("market.payment_was_completed_but_verification"), "error");
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
      console.error("Payment error:", error);
      notify(t("market.something_went_wrong_while_processing_"), "error");
    } finally {
      setPaying(false);
    }
  };

  // ------------------------------------------------------- delete equipment
  const deleteEquipment = async (item) => {
    const yes = await confirmDialog(t("market.delete_confirm"), { confirmLabel: t("market.delete") });

    if (!yes) return;

    try {
      const res = await fetch(`${API_URL}/equipment/${item.id}`, { method: "DELETE", headers: jsonHeaders() });

      if (res.status === 401) {
        sessionExpired();
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));

        notify(typeof data.detail === "string" ? serverText(t, data.detail) : t("market.err_delete"), "error");
        return;
      }

      notify(t("market.deleted"), "success");
      fetchEquipment();
    } catch (error) {
      console.error("Delete equipment error:", error);
      notify(t("market.err_delete"), "error");
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
        subtitle={t("market.rent_agricultural_equipment_from_nearb")}
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
            <Calendar size={20} />{" "}{t("market.my_rentals_bookings")}
          </h3>

          <div className="rental-list">
            {myRentals.map((rental) => (
              <div key={rental.id} className="rental-row">
                <span className="rental-id">#{rental.id}</span>

                <span className="rental-what">
                  {t("market.equipment_n", { id: rental.equipment_id })}
                  <small>
                    {rental.start_date} → {rental.end_date}
                  </small>
                </span>

                <strong>₹{rental.total_amount}</strong>

                <span
                  className={`rental-status status-${String(rental.status).toLowerCase().replace(/\s+/g, "-")}`}
                >
                  {enumText(t, "status.", rental.status)}
                  {rental.payment_status === "Paid" ? " · " + enumText(t, "status.", "Paid") : ""}
                </span>

                {rental.status === "Pending" && rental.payment_status !== "Paid" && String(rental.expires_at) > new Date().toISOString() && (
                  <span className="rental-pay">
                    <Button size="sm" loading={paying} icon={CreditCard} onClick={() => payRental(rental, t("market.equipment_n", { id: rental.equipment_id }))}>
                      {t("market.pay_now")}
                    </Button>

                    <small>{t("market.pay_before", { when: String(rental.start_at).slice(0, 16).replace("T", " ") })}</small>
                  </span>
                )}
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
            placeholder={t("market.search_equipment_owner_or_location")}
            aria-label={t("market.search_equipment")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <VoiceMic lang={lang} t={t} onText={(text) => setSearch(text)} />

          <Button
            variant={nearMe ? "primary" : "ghost"}
            icon={Navigation}
            onClick={() => (nearMe ? setNearMe(null) : getPosition(setNearMe))}
          >
            {nearMe ? t("market.radius_clear", { km: radiusKm }) : t("btn_near_me")}
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
              <span className="note">{t("market.search_radius")}</span>

              <Segmented
                ariaLabel="radius"
                value={radiusKm}
                onChange={setRadiusKm}
                options={[5, 10, 25, 50].map((km) => [km, t("common.km_value", { n: km })])}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <div className="chip-scroll" role="group" aria-label={t("market.category")}>
          {["All", ...CATEGORIES].map((name) => (
            <Chip key={name} active={category === name} onClick={() => setCategory(name)}>
              {name === "All" ? t("cat.all") : cat(name)}
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
          title={nearMe ? t("market.none_within", { km: radiusKm }) : t("market.none_found")}
          text={
            nearMe
              ? t("market.try_wider")
              : t("market.try_different")
          }
          action={
            <Button icon={Plus} onClick={() => setShowAdd(true)}>
              {t("market.list_equipment_2")}
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
                    <img src={directImageUrl(item.image_url)} alt={item.equipment_name} referrerPolicy="no-referrer" loading="lazy" />
                  ) : (
                    <Icon size={64} className="media-icon" />
                  )}

                  <Pill tone={available ? "good" : "warn"} className="equipment-status">
                    {item.availability}
                  </Pill>

                  {item.location_live && (
                    <span className="live-badge">
                      <span className="live-dot" />{" "}{t("market.live")}
                    </span>
                  )}
                </div>

                <div className="equipment-body">
                  <span className="equipment-category">{cat(item.category || "Other")}</span>

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
                        <Navigation size={14} /> {t("market.km_away", { n: item.distance_km })}
                      </li>
                    )}

                    {item.location_geo && (
                      <li>
                        <Radio size={14} />
                        {item.location_live ? (
                          ` ${t("market.live_location")} `
                        ) : (
                          ` ${t("market.gps_seen", { time: (item.location_updated_at || "").slice(0, 16).replace("T", " ") })} `
                        )}
                        <a
                          href={`https://www.google.com/maps?q=${item.location_geo.lat},${item.location_geo.lng}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {t("market.map")}
                        </a>
                      </li>
                    )}
                  </ul>

                  <div className="equipment-foot">
                    <div className="equipment-price">
                      <strong>₹{item.price_per_day}</strong>
                      <small>{t("common.day")}</small>
                      {item.price_per_hour && <span className="hourly">{t("market.or_per_hour", { price: item.price_per_hour })}</span>}
                    </div>

                    <div className="equipment-actions">
                      {user && item.owner_id === user.id && (
                        <Button size="sm" variant="ghost" icon={Trash2} onClick={() => deleteEquipment(item)}>
                          {t("market.delete")}
                        </Button>
                      )}

                      {available && (
                        <Button size="sm" onClick={() => openRental(item)}>
                          {t("btn_rent")}
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>
      )}

      {/* --------------------------------------------------- add equipment */}
      <Modal open={showAdd} onClose={() => setShowAdd(false)} title={t("market.list_your_equipment_2")} size="md">
        <ModalHead title={t("market.list_your_equipment")} subtitle={t("market.farmers_near_you_will_be_able")} onClose={() => setShowAdd(false)} />

        <div className="form-grid">
          <Input id="eq-name" label={t("market.equipment_name_2")} placeholder={t("market.equipment_name")} value={addForm.name} onChange={(e) => setAdd("name", e.target.value)} />

          <Select
            id="eq-category"
            label={t("market.category")}
            value={addForm.category}
            onChange={(e) => setAdd("category", e.target.value)}
          >
            <option value="">{t("market.select_category")}</option>
            {CATEGORIES.map((name) => (
              <option key={name} value={name}>
                {cat(name)}
              </option>
            ))}
          </Select>

          <div className="two-col">
            <Input id="eq-owner" label={t("market.owner_name_2")} icon={User} placeholder={t("market.owner_name")} value={addForm.owner} onChange={(e) => setAdd("owner", e.target.value)} />

            <Input id="eq-contact" label={t("market.contact_number_2")} icon={Phone} placeholder={t("market.contact_number")} value={addForm.contact} onChange={(e) => setAdd("contact", e.target.value)} />
          </div>

          <Input id="eq-location" label={t("market.location")} icon={MapPin} placeholder={t("market.location")} value={addForm.location} onChange={(e) => setAdd("location", e.target.value)} />

          <div className="two-col">
            <Input id="eq-day" label={t("market.price_per_day_2")} type="number" placeholder={t("market.price_per_day")} value={addForm.perDay} onChange={(e) => setAdd("perDay", e.target.value)} />

            <Input
              id="eq-hour"
              label={t("market.price_per_hour")}
              type="number"
              placeholder={t("market.optional_enables_hourly_booking")}
              value={addForm.perHour}
              onChange={(e) => setAdd("perHour", e.target.value)}
            />
          </div>

          <div className="gps-box">
            <Button variant={addCoords ? "soft" : "ghost"} icon={Navigation} onClick={() => getPosition(setAddCoords)}>
              {addCoords ? t("market.location_captured") : t("market.use_current_location")}
            </Button>

            <span className="note">
              {addCoords
                ? t("market.gps_set", { lat: addCoords.lat.toFixed(4), lng: addCoords.lng.toFixed(4) })
                : t("market.needed_for_search")}
            </span>
          </div>

          <Input id="eq-image" label={t("market.photo_link_optional")} placeholder={t("market.equipment_image_url")} value={addForm.image} onChange={(e) => setAdd("image", e.target.value)} />

          <TextArea id="eq-desc" label={t("market.description")} placeholder={t("market.equipment_description")} rows="3" value={addForm.description} onChange={(e) => setAdd("description", e.target.value)} />
        </div>

        <div className="modal-actions">
          <Button variant="ghost" onClick={() => setShowAdd(false)}>
            {t("market.cancel")}
          </Button>

          <Button loading={adding} icon={Plus} onClick={addEquipment}>
            {t("market.list_equipment")}
          </Button>
        </div>
      </Modal>

      {/* ------------------------------------------------------ rent + pay */}
      <Modal open={Boolean(selected)} onClose={closeRental} title={t("market.rent_equipment")} size="md">
        {selected && (
          <>
            <ModalHead
              title={t("market.rent_equipment_title")}
              subtitle={t("market.choose_when")}
              onClose={closeRental}
            />

            <div className="rent-preview">
              {selected.image_url ? (
                <img src={directImageUrl(selected.image_url)} alt={selected.equipment_name} referrerPolicy="no-referrer" />
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
              {(
                <motion.div
                  key="details"
                  className="form-grid"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="two-col">
                    <Input id="rent-name" label={t("market.your_name_2")} icon={User} placeholder={t("market.your_name")} value={renterName} onChange={(e) => setRenterName(e.target.value)} />

                    <Input id="rent-phone" label={t("market.your_phone")} icon={Phone} type="tel" placeholder={t("market.your_phone_number")} value={renterPhone} onChange={(e) => setRenterPhone(e.target.value)} />
                  </div>

                  <div className="field">
                    <span className="field-label">{t("market.rental_period_2")}</span>

                    {selected.price_per_hour && (
                      <Segmented
                        ariaLabel="booking"
                        value={bookingType}
                        onChange={setBookingType}
                        options={[
                          ["day", t("market.by_day")],
                          ["hour", t("market.by_hour")],
                        ]}
                      />
                    )}
                  </div>

                  {!isHourly ? (
                    <div className="two-col">
                      <Input
                        id="rent-start"
                        label={t("market.start_date")}
                        type="date"
                        value={startDate}
                        min={earliestDate()}
                        onChange={(e) => setStartDate(e.target.value)}
                      />

                      <Input
                        id="rent-end"
                        label={t("market.end_date")}
                        type="date"
                        value={endDate}
                        min={startDate || earliestDate()}
                        onChange={(e) => setEndDate(e.target.value)}
                      />
                    </div>
                  ) : (
                    <div className="two-col">
                      <Input id="rent-start-t" label={t("market.start_time")} type="datetime-local" step="900" min={`${earliestDate()}T00:00`} value={startTime} onChange={(e) => setStartTime(e.target.value)} />

                      <Input id="rent-end-t" label={t("market.end_time")} type="datetime-local" step="900" value={endTime} min={startTime || `${earliestDate()}T00:00`} onChange={(e) => setEndTime(e.target.value)} />
                    </div>
                  )}

                  <p className="secure-note">
                    <Calendar size={14} />{" "}{t("market.earliest_start", { date: earliestDate() })}
                  </p>

                  {bookedSlots.length > 0 && (
                    <div className="booked">
                      <strong>
                        <Clock size={14} />{" "}{t("market.already_booked")}
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
                        <h4>{t("market.booking_summary")}</h4>

                        <div className="summary-row">
                          <span>{t("market.equipment")}</span>
                          <strong>{selected.equipment_name}</strong>
                        </div>

                        <div className="summary-row">
                          <span>{t(isHourly ? "market.price_per_hour_row" : "market.price_per_day_row")}</span>
                          <strong>₹{rentalRate}</strong>
                        </div>

                        <div className="summary-row">
                          <span>{t(isHourly ? "market.rental_hours" : "market.rental_days")}</span>

                          <strong>
                            {count(rentalUnits)}
                          </strong>
                        </div>

                        <div className="summary-row total">
                          <span>{t("market.total_amount")}</span>
                          <strong>₹{rentalTotal.toLocaleString("en-IN")}</strong>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <Button size="lg" block loading={paying} icon={Calendar} onClick={bookNow}>
                    {t("market.book_now")}
                  </Button>

                  <p className="secure-note">
                    <Clock size={14} />{" "}{t("market.held_until_start")}
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
