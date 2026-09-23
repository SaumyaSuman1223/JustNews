/** The sidebar's collapsed state. Read by the app layout on the server so
 * the first paint is already the reader's chosen width; written by
 * SidebarCollapse. Its own module because a "use client" file cannot hand a
 * plain constant to a server component. */
export const SIDEBAR_COOKIE = "jn_sidebar";
