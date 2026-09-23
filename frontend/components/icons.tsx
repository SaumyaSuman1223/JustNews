/**
 * The navigation icon set.
 *
 * One family, drawn on a 24-unit grid at a single 1.5 stroke, sized by the
 * `em`-relative default so an icon scales with the label beside it rather
 * than needing a size prop at every call site. `currentColor` throughout, so
 * active and hover states are a colour change on the parent and nothing here
 * knows about theme.
 *
 * Every icon is `aria-hidden`: each one sits next to a real text label in the
 * navigation, so announcing it again would just make a screen reader say
 * everything twice. The design system's rule is that icons are secondary to
 * typography - if an icon ever appears without a label, it needs its own
 * accessible name and this default is wrong for it.
 */
type IconProps = { className?: string };

function Icon({ children, className }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="1.25em"
      height="1.25em"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export function HomeIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M3 10.2 12 3l9 7.2" />
      <path d="M5.5 8.8V20h13V8.8" />
      <path d="M9.8 20v-6.2h4.4V20" />
    </Icon>
  );
}

/** An open publication - Aquila is a newspaper, not a compass or a globe. */
export function AquilaIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 6.4C10.3 5.2 8.2 4.6 5.5 4.6H3v13h2.5c2.7 0 4.8.6 6.5 1.8" />
      <path d="M12 6.4c1.7-1.2 3.8-1.8 6.5-1.8H21v13h-2.5c-2.7 0-4.8.6-6.5 1.8" />
      <path d="M12 6.4v13" />
    </Icon>
  );
}

/** Stacked sheets - the desk holds several topics at once. */
export function DeskIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m12 3 9 4.6-9 4.6-9-4.6L12 3Z" />
      <path d="m3 12.4 9 4.6 9-4.6" />
      <path d="m3 16.9 9 4.6 9-4.6" />
    </Icon>
  );
}

export function SavedIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M6.5 3.8h11v17l-5.5-4.2-5.5 4.2v-17Z" />
    </Icon>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="10.8" cy="10.8" r="6.8" />
      <path d="m15.8 15.8 4.4 4.4" />
    </Icon>
  );
}

export function SettingsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="3.2" />
      <path d="M12 2.8v2.6M12 18.6v2.6M4.5 4.5l1.9 1.9M17.6 17.6l1.9 1.9M2.8 12h2.6M18.6 12h2.6M4.5 19.5l1.9-1.9M17.6 6.4l1.9-1.9" />
    </Icon>
  );
}

export function ProfileIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="8.4" r="3.9" />
      <path d="M4.8 20.2c0-3.6 3.2-5.9 7.2-5.9s7.2 2.3 7.2 5.9" />
    </Icon>
  );
}

export function DiscoverIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m15.5 8.5-2.2 4.8-4.8 2.2 2.2-4.8z" />
    </Icon>
  );
}

export function HistoryIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 12a8 8 0 1 0 2.4-5.7" />
      <path d="M4 4.5v3.8h3.8" />
      <path d="M12 8v4.2l2.8 1.8" />
    </Icon>
  );
}

/** The sidebar's own collapse control: a panel with its edge drawn in. */
export function PanelIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="3.5" y="4.5" width="17" height="15" rx="2" />
      <path d="M9 4.5v15" />
    </Icon>
  );
}

export function MenuIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Icon>
  );
}

export function HeartIcon(props: IconProps & { filled?: boolean }) {
  const { filled, ...rest } = props;
  return (
    <Icon {...rest}>
      <path
        d="M12 19.5s-7-4.3-7-9.4A3.9 3.9 0 0 1 12 8a3.9 3.9 0 0 1 7 2.1c0 5.1-7 9.4-7 9.4z"
        fill={filled ? "currentColor" : "none"}
      />
    </Icon>
  );
}

export function MoreIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="6" cy="12" r="0.9" fill="currentColor" />
      <circle cx="12" cy="12" r="0.9" fill="currentColor" />
      <circle cx="18" cy="12" r="0.9" fill="currentColor" />
    </Icon>
  );
}

export function ShareIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 15V4" />
      <path d="m8 7.5 4-3.5 4 3.5" />
      <path d="M6 12v6.5h12V12" />
    </Icon>
  );
}

export function SlidersIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M6 4v5M6 13v7M12 4v9M12 17v3M18 4v3M18 11v9" />
      <path d="M4 11h4M10 15h4M16 9h4" />
    </Icon>
  );
}

export function ClockIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </Icon>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m7 10 5 5 5-5" />
    </Icon>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M6 6l12 12M18 6 6 18" />
    </Icon>
  );
}

export function ExternalIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M14 4h6v6" />
      <path d="M20 4 11 13" />
      <path d="M18 14v5.5H4.5V6H10" />
    </Icon>
  );
}
