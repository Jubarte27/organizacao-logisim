package com.cburch.logisim.std.memory;

import com.cburch.logisim.file.Loader;
import com.cburch.logisim.file.LogisimFile;
import com.cburch.logisim.circuit.Circuit;
import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.circuit.Propagator;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.data.Bounds;
import com.cburch.logisim.data.Location;
import com.cburch.logisim.data.Value;
import com.cburch.logisim.gui.hex.HexFile;
import com.cburch.logisim.instance.Instance;
import com.cburch.logisim.instance.InstanceState;
import com.cburch.logisim.instance.StdAttr;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.wiring.Pin;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.*;

public class CircuitSimulator {

    public static class MemoryRecord {
        public Component component;
        public CircuitState circuitState;
        public String circuitName;
        public String hierarchyPath;
        public String type; // "RAM" or "ROM"
        public String label;
        public Location location;
        public int addrBits;
        public int dataBits;
        public MemContents contents;
        public boolean isTarget = false;

        public String getIdentifier() {
            String lbl = (label != null && !label.trim().isEmpty()) ? label.trim() : "<unlabeled>";
            return type + " [" + lbl + "] at " + location + " in " + hierarchyPath;
        }
    }

    public static class RegisterRecord {
        public String hierarchyPath;
        public String label;
        public Location location;
        public int width;
        public int value;

        public RegisterRecord(String hierarchyPath, String label, Location location, int width, int value) {
            this.hierarchyPath = hierarchyPath;
            this.label = label;
            this.location = location;
            this.width = width;
            this.value = value;
        }
    }

    public static class SimResult {
        public int totalCycles;
        public String haltReason;
        public int[] registerBank = new int[32];
        public List<RegisterRecord> namedRegisters = new ArrayList<>();
        public List<MemoryRecord> memories = new ArrayList<>();
    }

    private static final String[] ABI_NAMES = {
        "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
        "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
        "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
        "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"
    };

    // Recursively collect all memory components across the circuit hierarchy
    public static void collectMemories(CircuitState state, String path, List<MemoryRecord> out) {
        Circuit circuit = state.getCircuit();
        String currentPath = path.isEmpty() ? circuit.getName() : path;

        for (Component c : circuit.getNonWires()) {
            if (c.getFactory() instanceof Mem) {
                Mem memFactory = (Mem) c.getFactory();
                MemoryRecord rec = new MemoryRecord();
                rec.component = c;
                rec.circuitState = state;
                rec.circuitName = circuit.getName();
                rec.hierarchyPath = currentPath;
                rec.type = (memFactory instanceof Ram) ? "RAM" : "ROM";
                rec.label = c.getAttributeSet().getValue(StdAttr.LABEL);
                rec.location = c.getLocation();
                rec.addrBits = c.getAttributeSet().getValue(Mem.ADDR_ATTR).getWidth();
                rec.dataBits = c.getAttributeSet().getValue(Mem.DATA_ATTR).getWidth();

                InstanceState iState = state.getInstanceState(c);
                MemState mState = memFactory.getState(iState);
                rec.contents = (mState != null) ? mState.getContents() : null;

                out.add(rec);
            }
        }

        for (CircuitState sub : state.getSubstates()) {
            collectMemories(sub, currentPath + "/" + sub.getCircuit().getName(), out);
        }
    }

    // Collect all named registers across the circuit hierarchy
    public static void collectNamedRegisters(CircuitState state, String path, List<RegisterRecord> out, Set<Component> exclude) {
        Circuit circuit = state.getCircuit();
        String currentPath = path.isEmpty() ? circuit.getName() : path;

        for (Component c : circuit.getNonWires()) {
            if (exclude != null && exclude.contains(c)) {
                continue;
            }
            if (c.getFactory().getName().equals("Register")) {
                String label = c.getAttributeSet().getValue(StdAttr.LABEL);
                if (label != null && !label.trim().isEmpty()) {
                    Object data = state.getData(c);
                    int val = (data instanceof RegisterData) ? ((RegisterData) data).getValue() : 0;
                    int width = 32;
                    try {
                        width = c.getAttributeSet().getValue(StdAttr.WIDTH).getWidth();
                    } catch (Exception ignored) {}
                    out.add(new RegisterRecord(currentPath, label.trim(), c.getLocation(), width, val));
                }
            }
        }

        for (CircuitState sub : state.getSubstates()) {
            collectNamedRegisters(sub, currentPath + "/" + sub.getCircuit().getName(), out, exclude);
        }
    }

    // Find the Register Bank substate and its 32 registers
    public static CircuitState findRegisterBankState(CircuitState rootState) {
        for (CircuitState sub : rootState.getSubstates()) {
            String name = sub.getCircuit().getName().toLowerCase();
            if (name.contains("register bank") || name.contains("banco")) {
                return sub;
            }
        }
        return null;
    }

    public static List<Component> getSortedBankRegisters(CircuitState rbState) {
        List<Component> regs = new ArrayList<>();
        for (Component c : rbState.getCircuit().getNonWires()) {
            if (c.getFactory().getName().equals("Register")) {
                regs.add(c);
            }
        }
        regs.sort(Comparator.comparingInt(c -> c.getLocation().getY()));
        return regs;
    }

    // Smart heuristic to pick the instruction / primary target memory
    public static MemoryRecord pickTargetMemory(List<MemoryRecord> memories, String userTarget) {
        if (memories.isEmpty()) {
            return null;
        }

        // 1. If user gave an explicit target string
        if (userTarget != null && !userTarget.trim().isEmpty()) {
            String target = userTarget.trim().toLowerCase();
            // Try matching location e.g. "(310,360)" or "310,360"
            for (MemoryRecord m : memories) {
                String locStr = m.location.toString();
                if (locStr.equalsIgnoreCase(target) || locStr.replace(" ", "").equalsIgnoreCase(target.replace(" ", ""))) {
                    return m;
                }
            }
            // Try matching label
            for (MemoryRecord m : memories) {
                if (m.label != null && m.label.toLowerCase().contains(target)) {
                    return m;
                }
            }
            // Try matching type (e.g. "rom" or "ram")
            for (MemoryRecord m : memories) {
                if (m.type.equalsIgnoreCase(target) && m.dataBits == 32) {
                    return m;
                }
            }
        }

        // 2. Look for top-level 32-bit memories
        List<MemoryRecord> top32 = new ArrayList<>();
        for (MemoryRecord m : memories) {
            if (m.hierarchyPath.equals(m.circuitName) && m.dataBits == 32) {
                top32.add(m);
            }
        }

        if (top32.size() == 1) {
            return top32.get(0);
        }

        if (top32.size() > 1) {
            // In Monociclo: ROM (310,360) is instruction memory, RAM (890,360) is data memory.
            // Prefer ROM if present among top 32-bit memories
            for (MemoryRecord m : top32) {
                if (m.type.equals("ROM")) {
                    return m;
                }
            }
            // In Pipeline: both are RAM! RAM at (240,550) is instruction RAM (lower X), RAM at (960,560) is data RAM.
            top32.sort(Comparator.comparingInt(m -> m.location.getX()));
            return top32.get(0);
        }

        // Fallback: any 32-bit memory
        for (MemoryRecord m : memories) {
            if (m.dataBits == 32) {
                return m;
            }
        }

        return memories.get(0);
    }

    public static void main(String[] args) {
        String circPath = null;
        String memPath = null;
        String dataMemPath = null;
        String userTarget = null;
        String jsonOutPath = null;
        int maxCycles = 1000;
        boolean verbose = false;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--circ":
                    if (i + 1 < args.length) circPath = args[++i];
                    break;
                case "--mem":
                    if (i + 1 < args.length) memPath = args[++i];
                    break;
                case "--data-mem":
                    if (i + 1 < args.length) dataMemPath = args[++i];
                    break;
                case "--target-mem":
                    if (i + 1 < args.length) userTarget = args[++i];
                    break;
                case "--cycles":
                    if (i + 1 < args.length) maxCycles = Integer.parseInt(args[++i]);
                    break;
                case "--json-out":
                    if (i + 1 < args.length) jsonOutPath = args[++i];
                    break;
                case "--verbose":
                    verbose = true;
                    break;
            }
        }

        if (circPath == null) {
            System.err.println("Error: --circ <circuit.circ> is required.");
            System.exit(1);
        }

        try {
            File circFile = new File(circPath);
            if (!circFile.exists()) {
                System.err.println("Error: Circuit file not found: " + circPath);
                System.exit(1);
            }

            // Load circuit purely in-memory. Does NOT modify the original file.
            Loader loader = new Loader(null);
            LogisimFile logisimFile = loader.openLogisimFile(circFile);
            Circuit mainCircuit = logisimFile.getMainCircuit();
            Project project = new Project(logisimFile);
            CircuitState state = new CircuitState(project, mainCircuit);
            Propagator prop = state.getPropagator();
            prop.propagate();

            // Collect all memories
            List<MemoryRecord> memories = new ArrayList<>();
            collectMemories(state, "", memories);

            // Load memory file into target memory
            MemoryRecord targetMem = null;
            if (memPath != null) {
                File memFile = new File(memPath);
                if (!memFile.exists()) {
                    System.err.println("Error: Memory file not found: " + memPath);
                    System.exit(1);
                }
                targetMem = pickTargetMemory(memories, userTarget);
                if (targetMem == null || targetMem.contents == null) {
                    System.err.println("Error: No suitable target memory found to load " + memPath);
                    System.exit(1);
                }
                targetMem.isTarget = true;
                HexFile.open(targetMem.contents, memFile);
                if (verbose) {
                    System.out.println("Loaded " + memPath + " into " + targetMem.getIdentifier());
                }
            }

            // Load optional data memory file
            if (dataMemPath != null) {
                File dataFile = new File(dataMemPath);
                if (!dataFile.exists()) {
                    System.err.println("Error: Data memory file not found: " + dataMemPath);
                    System.exit(1);
                }
                MemoryRecord dataMem = null;
                for (MemoryRecord m : memories) {
                    if (m != targetMem && m.type.equals("RAM") && m.dataBits == 32) {
                        dataMem = m;
                        break;
                    }
                }
                if (dataMem != null && dataMem.contents != null) {
                    HexFile.open(dataMem.contents, dataFile);
                    if (verbose) {
                        System.out.println("Loaded " + dataMemPath + " into " + dataMem.getIdentifier());
                    }
                }
            }

            // Repropagate after loading memory
            prop.propagate();

            // Find Register Bank
            CircuitState rbState = findRegisterBankState(state);
            List<Component> bankRegisters = (rbState != null) ? getSortedBankRegisters(rbState) : Collections.emptyList();
            Set<Component> excludeFromNamed = new HashSet<>(bankRegisters);

            // Find PC component if exists in main circuit
            Component pcComponent = null;
            for (Component c : mainCircuit.getNonWires()) {
                if (c.getFactory().getName().equals("Register")) {
                    String lbl = c.getAttributeSet().getValue(StdAttr.LABEL);
                    if (lbl != null && lbl.equalsIgnoreCase("PC")) {
                        pcComponent = c;
                        break;
                    }
                }
            }

            // Check for halt pin in main circuit
            Component haltPin = null;
            for (Component c : mainCircuit.getNonWires()) {
                if (c.getFactory() instanceof Pin) {
                    String lbl = c.getAttributeSet().getValue(StdAttr.LABEL);
                    if (lbl != null && lbl.equalsIgnoreCase("halt")) {
                        haltPin = c;
                        break;
                    }
                }
            }

            // Simulation loop
            int cycle = 0;
            String haltReason = "Max cycles (" + maxCycles + ") reached";
            int lastPc = -1;
            int stablePcCount = 0;
            int maxStableCycles = 25; // 25 cycles with identical PC indicates halt/infinite loop

            for (cycle = 0; cycle < maxCycles; cycle++) {
                // Check halt pin
                if (haltPin != null) {
                    InstanceState pinState = state.getInstanceState(haltPin);
                    Value val = Pin.FACTORY.getValue(pinState);
                    if (val != null && val.equals(Value.TRUE)) {
                        haltReason = "Halt pin asserted TRUE";
                        break;
                    }
                }

                // Check PC stability
                if (pcComponent != null) {
                    Object pcData = state.getData(pcComponent);
                    int curPc = (pcData instanceof RegisterData) ? ((RegisterData) pcData).getValue() : 0;
                    if (curPc == lastPc && curPc != 0) {
                        stablePcCount++;
                        if (stablePcCount >= maxStableCycles) {
                            haltReason = "PC stabilized at 0x" + Integer.toHexString(curPc) + " for " + stablePcCount + " cycles";
                            break;
                        }
                    } else {
                        stablePcCount = 0;
                        lastPc = curPc;
                    }
                }

                // Check oscillation
                if (prop.isOscillating()) {
                    haltReason = "Circuit oscillation detected";
                    break;
                }

                // Advance clock: low -> high -> low
                prop.tick();
                prop.propagate();
                prop.tick();
                prop.propagate();
            }

            SimResult result = new SimResult();
            result.totalCycles = cycle;
            result.haltReason = haltReason;

            // Extract Register Bank values
            if (rbState != null && bankRegisters.size() >= 32) {
                for (int i = 0; i < 32; i++) {
                    Component reg = bankRegisters.get(i);
                    Object data = rbState.getData(reg);
                    result.registerBank[i] = (data instanceof RegisterData) ? ((RegisterData) data).getValue() : 0;
                }
                // x0 is always hardwired to 0 in RISC-V
                result.registerBank[0] = 0;
            }

            // Extract named registers
            collectNamedRegisters(state, "", result.namedRegisters, excludeFromNamed);
            result.namedRegisters.sort(Comparator.comparing(r -> r.hierarchyPath + "/" + r.label));

            // Extract memories
            result.memories = memories;

            // Output JSON if requested
            if (jsonOutPath != null) {
                writeJsonResult(result, jsonOutPath);
            }

            // Shutdown simulator threads cleanly
            project.getSimulator().shutDown();
            System.exit(0);

        } catch (Exception e) {
            e.printStackTrace();
            System.exit(1);
        }
    }

    private static String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\b", "\\b")
                .replace("\f", "\\f")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }

    public static void writeJsonResult(SimResult result, String outPath) throws IOException {
        try (PrintWriter pw = new PrintWriter(new FileWriter(outPath))) {
            pw.println("{");
            pw.println("  \"totalCycles\": " + result.totalCycles + ",");
            pw.println("  \"haltReason\": \"" + escapeJson(result.haltReason) + "\",");

            // Register Bank
            pw.println("  \"registerBank\": [");
            for (int i = 0; i < 32; i++) {
                int val = result.registerBank[i];
                String hex = String.format("0x%08x", val);
                pw.printf("    {\"index\": %d, \"name\": \"x%d\", \"abi\": \"%s\", \"value\": %d, \"hex\": \"%s\"}%s\n",
                    i, i, ABI_NAMES[i], val, hex, (i < 31 ? "," : ""));
            }
            pw.println("  ],");

            // Named Registers
            pw.println("  \"namedRegisters\": [");
            for (int i = 0; i < result.namedRegisters.size(); i++) {
                RegisterRecord r = result.namedRegisters.get(i);
                String hex = String.format("0x%08x", r.value);
                pw.printf("    {\"hierarchy\": \"%s\", \"label\": \"%s\", \"location\": \"%s\", \"width\": %d, \"value\": %d, \"hex\": \"%s\"}%s\n",
                    escapeJson(r.hierarchyPath), escapeJson(r.label), escapeJson(r.location.toString()), r.width, r.value, hex,
                    (i < result.namedRegisters.size() - 1 ? "," : ""));
            }
            pw.println("  ],");

            // Memories
            pw.println("  \"memories\": [");
            for (int i = 0; i < result.memories.size(); i++) {
                MemoryRecord m = result.memories.get(i);
                pw.println("    {");
                pw.println("      \"type\": \"" + m.type + "\",");
                pw.println("      \"label\": \"" + escapeJson(m.label != null ? m.label : "") + "\",");
                pw.println("      \"hierarchy\": \"" + escapeJson(m.hierarchyPath) + "\",");
                pw.println("      \"location\": \"" + escapeJson(m.location.toString()) + "\",");
                pw.println("      \"addrBits\": " + m.addrBits + ",");
                pw.println("      \"dataBits\": " + m.dataBits + ",");
                pw.println("      \"isTarget\": " + m.isTarget + ",");

                // Non-zero words
                pw.println("      \"nonZeroEntries\": [");
                if (m.contents != null) {
                    long last = m.contents.getLastOffset();
                    boolean firstEntry = true;
                    for (long addr = 0; addr <= last; addr++) {
                        int val = m.contents.get(addr);
                        if (val != 0) {
                            if (!firstEntry) pw.println(",");
                            String hexVal = String.format("0x%08x", val);
                            pw.printf("        {\"addr\": %d, \"hexAddr\": \"0x%x\", \"value\": %d, \"hex\": \"%s\"}",
                                addr, addr, val, hexVal);
                            firstEntry = false;
                        }
                    }
                    if (!firstEntry) pw.println();
                }
                pw.println("      ]");
                pw.printf("    }%s\n", (i < result.memories.size() - 1 ? "," : ""));
            }
            pw.println("  ]");
            pw.println("}");
        }
    }
}
