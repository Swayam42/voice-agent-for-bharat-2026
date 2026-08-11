import { Caveat, Kalam, Noto_Sans_Oriya } from 'next/font/google';
import localFont from 'next/font/local';
import { headers } from 'next/headers';
import { GlobalClickSound } from '@/components/app/global-click-sound';
import { ThemeProvider } from '@/components/app/theme-provider';
import { ThemeToggle } from '@/components/app/theme-toggle';
import { cn } from '@/lib/shadcn/utils';
import { getAppConfig, getStyles } from '@/lib/utils';
import '@/styles/globals.css';

const caveat = Caveat({
  variable: '--font-display',
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
});

const kalam = Kalam({
  variable: '--font-hand',
  subsets: ['latin'],
  weight: ['300', '400', '700'],
});

const notoOriya = Noto_Sans_Oriya({
  variable: '--font-odia',
  subsets: ['oriya'],
  weight: ['400', '700'],
});

const commitMono = localFont({
  display: 'swap',
  variable: '--font-commit-mono',
  src: [
    {
      path: '../fonts/CommitMono-400-Regular.otf',
      weight: '400',
      style: 'normal',
    },
    {
      path: '../fonts/CommitMono-700-Regular.otf',
      weight: '700',
      style: 'normal',
    },
    {
      path: '../fonts/CommitMono-400-Italic.otf',
      weight: '400',
      style: 'italic',
    },
    {
      path: '../fonts/CommitMono-700-Italic.otf',
      weight: '700',
      style: 'italic',
    },
  ],
});

interface RootLayoutProps {
  children: React.ReactNode;
}

export default async function RootLayout({ children }: RootLayoutProps) {
  const hdrs = await headers();
  const appConfig = await getAppConfig(hdrs);
  const styles = getStyles(appConfig);
  const { pageTitle, pageDescription } = appConfig;

  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn(
        caveat.variable,
        kalam.variable,
        notoOriya.variable,
        commitMono.variable,
        'scroll-smooth antialiased'
      )}
    >
      <head>
        {styles && <style>{styles}</style>}
        <title>{pageTitle}</title>
        <meta name="description" content={pageDescription} />
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#fafaf8" media="(prefers-color-scheme: light)" />
        <meta name="theme-color" content="#1c1c1c" media="(prefers-color-scheme: dark)" />
      </head>
      <body className="overflow-x-hidden font-sans">
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          {/* Minimal top brand — phone friendly, no clutter */}
          <header className="pointer-events-none fixed top-0 left-0 z-50 flex w-full items-center justify-between px-5 pt-4 sm:px-6 sm:pt-5">
            <span className="font-display text-foreground/70 pointer-events-auto text-lg tracking-wide sm:text-3xl">
              Mo Saathi
            </span>
            <a
              href="/escalations"
              className="pointer-events-auto rounded-full border border-border bg-card/80 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur-sm transition-colors hover:text-foreground"
            >
              Help Requests
            </a>
          </header>

          <GlobalClickSound />
          {children}

          <div className="group fixed right-3 bottom-3 z-50 sm:right-5 sm:bottom-5">
            <ThemeToggle className="translate-y-16 opacity-40 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100 focus-within:translate-y-0 focus-within:opacity-100" />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
