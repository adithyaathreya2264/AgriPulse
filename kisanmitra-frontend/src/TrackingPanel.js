// Owners: share equipment location from this phone, or create a key for a
// GPS tracker device that reports on its own.
import { useEffect, useRef, useState } from "react";
import { notify, confirmDialog } from "./ui/notify";
import { Button } from "./ui/kit";
import { Copy, KeyRound, MapPin, Radio, Square } from "./ui/icons";

// A new position is sent when 30 s passed or the phone moved 50 m
const SEND_EVERY_MS = 30000;
const SEND_IF_MOVED_M = 50;

const distanceMeters = (a, b) => {
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;

  return 2 * 6371000 * Math.asin(Math.sqrt(h));
};

export default function TrackingPanel({ apiUrl, token, user, onChanged }) {
  const [items, setItems] = useState([]);
  const [sharingId, setSharingId] = useState(null);
  const [status, setStatus] = useState("");
  const [trackerKey, setTrackerKey] = useState(null);

  const watchRef = useRef(null);
  const lastSentRef = useRef({ time: 0, position: null });
  const wakeLockRef = useRef(null);

  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  const load = async () => {
    try {
      const res = await fetch(`${apiUrl}/equipment`);

      if (!res.ok) return;

      const all = await res.json();

      setItems(all.filter((item) => item.owner_id === user.id));
    } catch (error) {
      console.warn("Could not load equipment:", error.message);
    }
  };

  useEffect(() => {
    load();
    return stopSharing; // eslint-disable-line react-hooks/exhaustive-deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = async (equipmentId, coords) => {
    try {
      const res = await fetch(`${apiUrl}/equipment/${equipmentId}/location`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({
          latitude: coords.latitude,
          longitude: coords.longitude,
          accuracy_m: coords.accuracy,
        }),
      });

      if (res.ok) {
        setStatus(
          `Location sent at ${new Date().toLocaleTimeString()} (accuracy ~${Math.round(
            coords.accuracy || 0
          )} m)`
        );
        onChanged && onChanged();
      } else {
        setStatus("Could not send the location. Are you still logged in?");
      }
    } catch (error) {
      setStatus("No connection. Will retry with the next position.");
    }
  };

  const stopSharing = () => {
    if (watchRef.current !== null) {
      navigator.geolocation.clearWatch(watchRef.current);
      watchRef.current = null;
    }

    if (wakeLockRef.current) {
      wakeLockRef.current.release().catch(() => {});
      wakeLockRef.current = null;
    }

    setSharingId(null);
  };

  const startSharing = async (equipmentId) => {
    if (!navigator.geolocation) {
      notify("This browser cannot share location", "error");
      return;
    }

    stopSharing();
    setSharingId(equipmentId);
    setStatus("Waiting for GPS...");
    lastSentRef.current = { time: 0, position: null };

    // Keep the screen on: web pages stop tracking when the phone sleeps
    try {
      if (navigator.wakeLock) {
        wakeLockRef.current = await navigator.wakeLock.request("screen");
      }
    } catch (error) {
      console.warn("Screen wake lock not available:", error.message);
    }

    watchRef.current = navigator.geolocation.watchPosition(
      (position) => {
        const here = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };
        const last = lastSentRef.current;
        const now = Date.now();

        const due = now - last.time >= SEND_EVERY_MS;
        const moved =
          last.position && distanceMeters(last.position, here) >= SEND_IF_MOVED_M;

        if (!last.position || due || moved) {
          lastSentRef.current = { time: now, position: here };
          send(equipmentId, position.coords);
        }
      },
      (error) => {
        setStatus(
          error.code === 1
            ? "Location permission was denied. Allow location for this site."
            : "Could not get the GPS position."
        );
        stopSharing();
      },
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 30000 }
    );
  };

  const createKey = async (equipmentId) => {
    const yes = await confirmDialog(
      "Create a new tracker key? An existing key for this equipment stops working.",
      { confirmLabel: "Create key" }
    );

    if (!yes) return;

    try {
      const res = await fetch(`${apiUrl}/equipment/${equipmentId}/tracker-key`, {
        method: "POST",
        headers,
      });

      if (!res.ok) {
        notify("Could not create the key", "error");
        return;
      }

      const data = await res.json();

      setTrackerKey({ equipmentId, key: data.tracker_key });
    } catch (error) {
      notify("Could not reach the server", "error");
    }
  };

  if (items.length === 0) return null;

  return (
    <div className="card tracking-panel">
      <h3 className="card-title">
        <Radio size={20} /> My equipment — live location
      </h3>

      <p className="note">
        Farmers nearby see your equipment on the map while it reports its position. A web
        page can only track while it stays open on your phone; for tracking that keeps
        working, fit a GPS tracker and use its key.
      </p>

      {items.map((item) => (
        <div key={item.id} className="tracking-row">
          <div className="tracking-info">
            <strong>{item.equipment_name}</strong>

            <span className="note">
              {item.location_geo ? (
                item.location_live ? (
                  <span className="live-badge live-inline">
                    <span className="live-dot" /> live
                  </span>
                ) : (
                  ` last seen ${item.location_updated_at.slice(0, 16).replace("T", " ")}`
                )
              ) : (
                " no location yet"
              )}
              {item.location_source ? ` (${item.location_source})` : ""}
            </span>
          </div>

          <div className="tracking-actions">
            {sharingId === item.id ? (
              <Button size="sm" variant="danger" icon={Square} onClick={stopSharing}>
                Stop sharing
              </Button>
            ) : (
              <Button size="sm" variant="soft" icon={MapPin} onClick={() => startSharing(item.id)}>
                Share from this phone
              </Button>
            )}

            <Button size="sm" variant="ghost" icon={KeyRound} onClick={() => createKey(item.id)}>
              GPS tracker key
            </Button>
          </div>
        </div>
      ))}

      {sharingId !== null && <p className="callout callout-tip">{status}</p>}

      {trackerKey && (
        <div className="tracker-key-box">
          <p>
            <strong>Tracker key for equipment #{trackerKey.equipmentId}</strong> — shown only
            once, save it now:
          </p>

          <code>{trackerKey.key}</code>

          <Button
            size="sm"
            variant="soft"
            icon={Copy}
            onClick={() => navigator.clipboard && navigator.clipboard.writeText(trackerKey.key)}
          >
            Copy
          </Button>

          <p className="note">
            The device sends <code>POST {apiUrl}/tracker/update</code> with header{" "}
            <code>X-Tracker-Key</code> and JSON <code>{'{"latitude": 12.29, "longitude": 76.63}'}</code>,
            at most once every 5 seconds.
          </p>

          <Button size="sm" onClick={() => setTrackerKey(null)}>
            I saved it
          </Button>
        </div>
      )}
    </div>
  );
}
