import { motion } from "framer-motion";
import AuthFlow from "../AuthFlow";
import { Avatar, Pill } from "../ui/kit";
import { useT } from "../i18n";
import { BadgeCheck, Cake, MapPin, Phone, Sprout, Tractor } from "../ui/icons";

export default function ProfilePage({ apiUrl, token, user, onProfileSaved }) {
  const t = useT();

  const facts = [
    [Phone, t("profile.mobile"), `+91 ${user.phone}`],
    [Cake, t("profile.age"), user.age ? t("profile.years", { n: user.age }) : "-"],
    [MapPin, t("profile.location"), [user.village, user.district, user.state].filter(Boolean).join(", ") || "-"],
  ];

  return (
    <div className="page profile-page">
      <motion.section
        className="profile-hero"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Avatar name={user.name || user.phone} size={84} />

        <div className="profile-hero-text">
          <h1>{user.name || user.phone}</h1>

          <div className="chip-row">
            <Pill tone="good" icon={BadgeCheck}>
              {t("common.id_number", { code: user.user_code })}
            </Pill>

            <Pill tone="info" icon={user.role === "owner" ? Tractor : Sprout}>
              {user.role === "owner" ? t("common.role_owner") : t("common.role_farmer")}
            </Pill>
          </div>
        </div>

        <ul className="profile-facts">
          {facts.map(([Icon, label, value]) => (
            <li key={label}>
              <Icon size={16} />

              <span>
                <small>{label}</small>
                <strong>{value}</strong>
              </span>
            </li>
          ))}
        </ul>
      </motion.section>

      <AuthFlow
        apiUrl={apiUrl}
        token={token}
        user={user}
        mode="profile"
        onLoggedIn={() => {}}
        onProfileSaved={onProfileSaved}
      />
    </div>
  );
}
