import com.cburch.logisim.circuit.*;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.comp.EndData;
import com.cburch.logisim.data.*;
import com.cburch.logisim.file.*;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.memory.Ram;
import java.io.File;
import java.lang.reflect.Method;
import java.util.*;

/**
 * Harness headless para o RISCV_Multiciclo.circ.
 *
 *   java -cp /usr/share/logisim/logisim.jar:. MultiSim <arquivo.circ> <programa.mem> <ciclos>
 *
 * Carrega o programa na RAM (memoria unica: instrucoes + dados, igual ao "Load Image"
 * da GUI), da clock ciclo a ciclo e imprime, a cada borda de subida:
 *   - o estado da FSM (pino "Estado") e o PC;
 *   - a escrita no banco de registradores que acontece nessa borda;
 *   - a escrita na memoria que acontece nessa borda.
 * No fim imprime o banco de registradores e as palavras da memoria (so as nao nulas).
 */
public class MultiSim {

    public static void main(String[] args) throws Exception {
        File circ = new File(args[0]);
        File prog = new File(args[1]);
        int cycles = Integer.parseInt(args[2]);

        LogisimFile lf = new Loader(null).openLogisimFile(circ);
        Project proj = new Project(lf);
        Circuit main = lf.getMainCircuit();
        CircuitState st = new CircuitState(proj, main);
        Propagator prop = st.getPropagator();

        Component pc = null, regBank = null, ir = null, clock = null, ram = null, estado = null;
        for (Component c : main.getNonWires()) {
            String n = c.getFactory().getName();
            Object label = attr(c, "label");
            if (n.equals("Register") && "PC".equals(label)) pc = c;
            if (n.equals("RAM")) ram = c;
            if (n.equals("Clock")) clock = c;
            if (n.equals("Pin") && "Estado".equals(label)) estado = c;
            if (c.getFactory() instanceof SubcircuitFactory) {
                String sn = ((SubcircuitFactory) c.getFactory()).getSubcircuit().getName();
                if (sn.equals("Register Bank")) regBank = c;
                if (sn.equals("Instruction Register")) ir = c;
            }
        }

        ((Ram) ram.getFactory()).loadImage(st.getInstanceState(ram), prog);
        prop.propagate();

        SubcircuitFactory rbf = (SubcircuitFactory) regBank.getFactory();
        CircuitState rbs = rbf.getSubstate(st, regBank);
        List<Component> regs = new ArrayList<Component>();
        for (Component c : rbf.getSubcircuit().getNonWires())
            if (c.getFactory().getName().equals("Register")) regs.add(c);
        Collections.sort(regs, new Comparator<Component>() {
            public int compare(Component a, Component b) { return a.getLocation().getY() - b.getLocation().getY(); }
        });

        StringBuilder sb = new StringBuilder();
        int cyc = 0;
        while (cyc < cycles) {
            boolean low = st.getValue(clock.getEnd(0).getLocation()) != Value.TRUE;
            if (low) {   // a proxima transicao e' a borda de subida: amostra o que vai ser gravado
                sb.append(String.format("C %d E=%s PC=%s IR=%s", cyc, dec(st, estado.getEnd(0)),
                        hex(st, pc.getEnd(0)), hex(st, ir.getEnd(10))));
                if (st.getValue(regBank.getEnd(4).getLocation()) == Value.TRUE)
                    sb.append(String.format(" WB=%s:%s", dec(st, regBank.getEnd(2)), hex(st, regBank.getEnd(3))));
                if (st.getValue(ram.getEnd(6).getLocation()) == Value.TRUE)
                    sb.append(String.format(" MEM=%s:%s", word2byte(st, ram.getEnd(1)), hex(st, ram.getEnd(7))));
                sb.append('\n');
                cyc++;
            }
            prop.tick(); prop.propagate();
        }
        sb.append("---- registradores ----\n");
        for (int i = 1; i < regs.size(); i++) {
            String v = hex(rbs, regs.get(i).getEnd(0));
            if (!v.equals("00000000")) sb.append(String.format("x%d = %s%n", i, v));
        }
        sb.append("---- memoria de dados ----\n");
        Object ms = st.getData(ram);
        Method gc = ms.getClass().getMethod("getContents"); gc.setAccessible(true);
        Object mc = gc.invoke(ms);
        Method get = mc.getClass().getMethod("get", long.class); get.setAccessible(true);
        for (long a = 0; a < 0x4000; a++) {
            int v = (Integer) get.invoke(mc, a);
            if (v != 0) sb.append(String.format("[%08x] = %08x%n", a * 4, v));
        }
        System.out.print(sb);
        System.out.flush();
        System.exit(0);   // new Project(...) deixa uma thread nao-daemon viva
    }

    static Object attr(Component c, String name) {
        for (Attribute<?> a : c.getAttributeSet().getAttributes())
            if (a.getName().equals(name)) return c.getAttributeSet().getValue(a);
        return null;
    }
    static String hex(CircuitState st, EndData e) {
        Value v = st.getValue(e.getLocation());
        return v.isFullyDefined() ? String.format("%08x", v.toIntValue()) : v.toString().replace(' ', '_');
    }
    static String dec(CircuitState st, EndData e) {
        Value v = st.getValue(e.getLocation());
        return v.isFullyDefined() ? Integer.toString(v.toIntValue()) : v.toString().replace(' ', '_');
    }
    static String word2byte(CircuitState st, EndData e) {
        Value v = st.getValue(e.getLocation());
        return v.isFullyDefined() ? String.format("%08x", v.toIntValue() * 4) : v.toString().replace(' ', '_');
    }
}
