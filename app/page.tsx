import ReadingRoom from "@/components/reading-room";
import catalog from "@/data/catalog.json";

export default function Home() {
  return <ReadingRoom catalog={catalog} />;
}
