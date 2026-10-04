import { Combine, Cog, Drone, Droplets, Shovel, Sprout, Tractor, Truck, Wheat } from "../ui/icons";

export const CATEGORIES = [
  "Tractor",
  "Harvester",
  "Rotavator",
  "Cultivator",
  "Seeder",
  "Sprayer",
  "Drone",
  "Sprayer Drone",
  "Trailer",
  "Other",
];

const ICONS = {
  Tractor,
  Harvester: Combine,
  Rotavator: Cog,
  Cultivator: Shovel,
  Seeder: Sprout,
  Sprayer: Droplets,
  Drone,
  "Sprayer Drone": Drone,
  Trailer: Truck,
  Other: Wheat,
};

export const categoryIcon = (category) => ICONS[category] || Tractor;

export const categoryClass = (category) =>
  `cat-${String(category || "Other").replace(/\s+/g, "-").toLowerCase()}`;

// A Google Drive "share" link is a web page, not an image file. Turn it into a direct image link.
// Other links are used as they are. The Drive file must be shared as "Anyone with the link".
export const directImageUrl = (link) => {
  const url = String(link || "").trim();

  if (!url) return "";

  const drive =
    url.match(/drive\.google\.com\/file\/d\/([\w-]+)/) ||
    url.match(/drive\.google\.com\/(?:open|uc|thumbnail)\?(?:[^#]*&)?id=([\w-]+)/) ||
    url.match(/docs\.google\.com\/uc\?(?:[^#]*&)?id=([\w-]+)/);

  if (drive) return `https://drive.google.com/thumbnail?id=${drive[1]}&sz=w1000`;

  return url;
};
