import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      /**
       * Logos are uploaded through a server action, and the
       * default ceiling for one of those is 1MB - lower than the
       * 2MB the API itself accepts. Without this, a 1.4MB photo
       * is refused by the framework with a runtime error page
       * rather than by us with a sentence.
       *
       * 3MB rather than 2MB because the limit applies to the
       * whole multipart body, not just the file inside it.
       */
      bodySizeLimit: "3mb",
    },
  },
};

export default nextConfig;
