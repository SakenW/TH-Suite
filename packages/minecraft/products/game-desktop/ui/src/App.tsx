import { useState } from "react";
import { invoke } from "@tauri-apps/api/tauri";

function App() {
    const [greetMsg, setGreetMsg] = useState("");
    const [name, setName] = useState("");

    async function greet() {
        // Learn more about Tauri commands at https://tauri.app/v1/guides/features/command
        setGreetMsg(await invoke("greet", { name }));
    }

    return (
        <div className="container mx-auto p-4 dark:bg-zinc-950 dark:text-white min-h-screen">
            <h1 className="text-2xl font-bold mb-4">Minecraft Modpack Translator</h1>

            <div className="flex gap-2">
                <input
                    id="greet-input"
                    className="border p-2 rounded text-black"
                    onChange={(e) => setName(e.currentTarget.value)}
                    placeholder="Enter a name..."
                />
                <button type="button" onClick={greet} className="bg-blue-500 text-white px-4 py-2 rounded">
                    Greet
                </button>
            </div>

            <p className="mt-4">{greetMsg}</p>
        </div>
    );
}

export default App;
