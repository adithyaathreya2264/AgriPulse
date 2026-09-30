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
