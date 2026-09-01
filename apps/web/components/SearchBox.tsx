export function SearchBox({ locale }: { locale: string }) {
  return (
    <form className="search-box" action={`/${locale}/search`} role="search">
      <label className="visually-hidden" htmlFor="site-search">
        Search headlines
      </label>
      <input id="site-search" type="search" name="q" placeholder="Search headlines" />
      <button type="submit">Search</button>
    </form>
  );
}
