"use client";

import { useEffect, useRef } from "react";
import type * as AtlasType from "azure-maps-control";
import "azure-maps-control/dist/atlas.min.css";

type NearbyResource = {
  type: string;
  name: string;
  address?: string;
  latitude: number;
  longitude: number;
  distance_meters?: number;
};

type IncidentMapProps = {
  latitude?: number;
  longitude?: number;
  title?: string;
  description?: string;
  nearbyResources?: NearbyResource[];
};

export default function IncidentMap({
  latitude,
  longitude,
  title = "Incident Location",
  description = "Emergency location",
  nearbyResources = [],
}: IncidentMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<AtlasType.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || !latitude || !longitude) return;

    let disposed = false;

    import("azure-maps-control").then((atlas) => {
      if (disposed || !containerRef.current) return;

      const map = new atlas.Map(containerRef.current, {
        center: [longitude, latitude],
        zoom: 14,
        view: "Auto",
        authOptions: {
          authType: atlas.AuthenticationType.subscriptionKey,
          subscriptionKey: process.env.NEXT_PUBLIC_AZURE_MAPS_KEY!,
        },
      });
      mapInstanceRef.current = map;

      map.events.add("ready", () => {
        // Incident marker
        const incidentMarker = new atlas.HtmlMarker({
          position: [longitude, latitude],
          color: "Red",
          text: "!",
          popup: new atlas.Popup({
            content: `<div style="padding:10px"><b>${title}</b><br/>${description}</div>`,
            pixelOffset: [0, -30],
          }),
        });
        map.markers.add(incidentMarker);
        map.events.add("click", incidentMarker, () => incidentMarker.togglePopup());

        // Nearby resource markers
        nearbyResources.forEach((resource) => {
          const color =
            resource.type === "hospital"
              ? "DodgerBlue"
              : resource.type === "fire station"
              ? "Orange"
              : "Purple";

          const label =
            resource.type === "hospital"
              ? "H"
              : resource.type === "fire station"
              ? "F"
              : "P";

          const resourceMarker = new atlas.HtmlMarker({
            position: [resource.longitude, resource.latitude],
            color,
            text: label,
            popup: new atlas.Popup({
              content: `<div style="padding:10px"><b>${resource.name}</b><br/>${resource.type}<br/>${resource.address || ""}</div>`,
              pixelOffset: [0, -30],
            }),
          });
          map.markers.add(resourceMarker);
          map.events.add("click", resourceMarker, () => resourceMarker.togglePopup());
        });
      });
    });

    return () => {
      disposed = true;
      mapInstanceRef.current?.dispose();
      mapInstanceRef.current = null;
    };
  }, [latitude, longitude, title, description, nearbyResources]);

  if (!latitude || !longitude) {
    return (
      <div className="rounded border p-4 text-gray-500">
        No valid coordinates available.
      </div>
    );
  }

  return <div ref={containerRef} className="h-96 w-full rounded border" />;
}
