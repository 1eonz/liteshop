import { siteTitle } from '../src/site-data';

export default function HomePage(): JSX.Element {
  return (
    <main>
      <h1>{siteTitle}</h1>
      <p>商城官网</p>
    </main>
  );
}
