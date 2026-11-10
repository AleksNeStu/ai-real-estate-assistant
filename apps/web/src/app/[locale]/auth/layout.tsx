export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    // The auth screens are one column of 380px, centred on the page. The
    // measure is the card's, so the layout only centres and pads.
    <div className="flex min-h-[calc(100vh-4rem)] w-full items-start justify-center bg-background px-6 py-14">
      <div className="w-full max-w-[380px]">{children}</div>
    </div>
  );
}
