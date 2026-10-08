import { useCallback, useEffect, useState } from 'react';

export const SCREENS = ['store', 'experiments', 'pilot'] as const;
export type Screen = (typeof SCREENS)[number];

const ALIASES: Record<string, Screen> = { live: 'store', ask: 'experiments', lab: 'experiments', plan: 'pilot' };

function resolve(hash: string): Screen {
  const name = ALIASES[hash] ?? hash;
  return (SCREENS as readonly string[]).includes(name) ? (name as Screen) : 'store';
}

/** Mirrors the old app's #store/#experiments/#pilot hash nav — no router needed for three tabs. */
export function useHashRoute(): [Screen, (screen: Screen) => void] {
  const [screen, setScreen] = useState<Screen>(() => resolve(location.hash.slice(1)));

  useEffect(() => {
    const onHashChange = () => setScreen(resolve(location.hash.slice(1)));
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const navigate = useCallback((next: Screen) => {
    if (location.hash !== `#${next}`) location.hash = next;
    else setScreen(next);
  }, []);

  return [screen, navigate];
}
