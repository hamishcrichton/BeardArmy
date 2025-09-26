import React, { useEffect, useRef } from "react";

// Placeholder types for data; adjust to real artifact shape
type ChallengePoint = {
  id: number;
  video_id: string;
  lat: number;
  lng: number;
  title: string;
  restaurant: string;
  date_attempted?: string;
  result?: "success" | "failure" | "unknown";
  image_url?: string;
  address?: string;
  opening_hours?: string;
  country_code?: string;
  type?: string;
};

type Props = {
  data: ChallengePoint[];
  onSelect?: (id: number) => void;
};

/**
 * Minimal MapLibre-based map placeholder. In a real app, import maplibre-gl and supercluster,
 * render clusters and popups styled via CSS variables (see tokens.css).
 */
export function Map({ data, onSelect }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Lazy import to avoid SSR issues in Next.js
    let map: any;
    (async () => {
      const maplibre = await import("maplibre-gl");
      const MapLibreGL = maplibre.default;
      if (!ref.current) return;
      map = new MapLibreGL.Map({
        container: ref.current,
        style: "https://demotiles.maplibre.org/style.json",
        center: [0, 20],
        zoom: 1.5,
      });
      map.addControl(new MapLibreGL.NavigationControl({ showCompass: false }), "top-right");
      // TODO: add source/layers from GeoJSON built from `data`; add clustering
    })();
    return () => { if (map) map.remove(); };
  }, [data]);

  return (
    <div
      ref={ref}
      style={{
        width: "100%",
        height: "500px",
        borderRadius: "var(--bmf-radius-lg)",
        boxShadow: "var(--bmf-shadow-2)",
        background: "var(--bmf-color-bg-alt)",
      }}
    />
  );
}

