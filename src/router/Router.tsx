import React, { createContext, useContext, useEffect, useState, useMemo } from 'react';

export interface LocationState {
  pathname: string;
  search: string;
  searchParams: URLSearchParams;
}

export interface RouterContextValue extends LocationState {
  navigate: (to: string, options?: { replace?: boolean }) => void;
}

const RouterContext = createContext<RouterContextValue | null>(null);

function normalizePath(rawPath: string): string {
  if (!rawPath || rawPath === '') return '/';
  // Strip trailing slash unless it's just '/'
  const normalized = rawPath.startsWith('/') ? rawPath : `/${rawPath}`;
  if (normalized.length > 1 && normalized.endsWith('/')) {
    return normalized.slice(0, -1);
  }
  return normalized;
}

export const BrowserRouter: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentLocation, setCurrentLocation] = useState<LocationState>(() => {
    if (typeof window === 'undefined') {
      return { pathname: '/', search: '', searchParams: new URLSearchParams() };
    }
    return {
      pathname: normalizePath(window.location.pathname),
      search: window.location.search,
      searchParams: new URLSearchParams(window.location.search),
    };
  });

  useEffect(() => {
    const handlePopState = () => {
      setCurrentLocation({
        pathname: normalizePath(window.location.pathname),
        search: window.location.search,
        searchParams: new URLSearchParams(window.location.search),
      });
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = (to: string, options?: { replace?: boolean }) => {
    const [pathPart, searchPart] = to.split('?');
    const normalizedPath = normalizePath(pathPart || '/');
    const searchString = searchPart ? `?${searchPart}` : '';
    const fullUrl = `${normalizedPath}${searchString}`;

    if (options?.replace) {
      window.history.replaceState({}, '', fullUrl);
    } else {
      window.history.pushState({}, '', fullUrl);
    }

    setCurrentLocation({
      pathname: normalizedPath,
      search: searchString,
      searchParams: new URLSearchParams(searchString),
    });

    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
  };

  const contextValue = useMemo<RouterContextValue>(
    () => ({
      ...currentLocation,
      navigate,
    }),
    [currentLocation]
  );

  return <RouterContext.Provider value={contextValue}>{children}</RouterContext.Provider>;
};

export function useRouter(): RouterContextValue {
  const ctx = useContext(RouterContext);
  if (!ctx) {
    throw new Error('useRouter must be used within a <BrowserRouter>');
  }
  return ctx;
}

export function useNavigate() {
  const { navigate } = useRouter();
  return navigate;
}

export function useLocation(): LocationState {
  const { pathname, search, searchParams } = useRouter();
  return { pathname, search, searchParams };
}

export interface LinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  to: string;
  replace?: boolean;
}

export const Link: React.FC<LinkProps> = ({ to, replace, onClick, children, ...rest }) => {
  const { navigate } = useRouter();

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (onClick) onClick(e);
    if (!e.defaultPrevented && e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey) {
      e.preventDefault();
      navigate(to, { replace });
    }
  };

  return (
    <a href={to} onClick={handleClick} {...rest}>
      {children}
    </a>
  );
};
