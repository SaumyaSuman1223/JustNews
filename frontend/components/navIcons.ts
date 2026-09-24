import {
  AquilaIcon,
  DiscoverIcon,
  FollowingIcon,
  HistoryIcon,
  SavedIcon,
  SearchIcon,
  SettingsIcon,
} from "@/components/icons";
import type { NavItem } from "@/lib/navigation";

/** One icon per destination, shared by the sidebar and the mobile tab bar so
 * the two never disagree about what a place looks like. */
export const NAV_ICONS: Record<NavItem["id"], (props: { className?: string }) => React.JSX.Element> =
  {
    home: DiscoverIcon,
    aquila: AquilaIcon,
    search: SearchIcon,
    saved: SavedIcon,
    following: FollowingIcon,
    history: HistoryIcon,
    settings: SettingsIcon,
  };
