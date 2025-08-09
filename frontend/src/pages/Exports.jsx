import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";

export default function Exports() {
  const [items, setItems] = useState([]);
  const [recipeName, setRecipeName] = useState("Warm+Hot last 7 days with LinkedIn handle");

  const refresh = async () => setItems((await api.get(`/exports`)).data);
  useEffect(() => { refresh(); }, []);

  const createRecipe = async () => {
    await api.post(`/exports/recipe`, { recipe_name: recipeName, filter_spec: { priority_state: ["warm", "hot"], has_linkedin: true } });
    await refresh();
  };
  const generate = async () => {
    await api.post(`/exports/generate`, { recipe_name: recipeName });
    await refresh();
  };

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Exports</h2>
      <div className="bg-white rounded shadow p-3 mb-4 grid grid-cols-1 md:grid-cols-3 gap-2">
        <input className="border rounded px-2 py-1" value={recipeName} onChange={(e) => setRecipeName(e.target.value)} />
        <button onClick={createRecipe} className="px-3 py-1 bg-neutral-800 text-white rounded">Create Recipe</button>
        <button onClick={generate} className="px-3 py-1 bg-blue-600 text-white rounded">Generate</button>
      </div>

      <div className="bg-white rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-neutral-100 text-left">
              <th className="p-2">Recipe</th>
              <th className="p-2">Rows</th>
              <th className="p-2">File</th>
              <th className="p-2">Generated</th>
            </tr>
          </thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id} className="border-t">
                <td className="p-2">{e.recipe_name}</td>
                <td className="p-2">{e.row_count}</td>
                <td className="p-2">{e.file_url}</td>
                <td className="p-2">{phoenixTime(e.generated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}