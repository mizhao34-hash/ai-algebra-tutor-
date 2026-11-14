/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // No ESLint setup in this project; type errors still fail the build.
  eslint: { ignoreDuringBuilds: true },
};
export default nextConfig;
