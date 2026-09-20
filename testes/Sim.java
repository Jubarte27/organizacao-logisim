import com.cburch.logisim.circuit.*;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.data.*;
import com.cburch.logisim.file.*;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.circuit.SubcircuitFactory;
import java.io.File;
import java.util.*;

/**
 * Harness de simulacao headless para os .circ do RISC-V.
 *
 *   java -cp /usr/share/logisim/logisim.jar:. Sim <arquivo.circ> <ciclos>
 *
 * Imprime, a cada ciclo, o PC e (no fim) o banco de registradores.
 */
public class Sim {

    static Component pcReg;
    static CircuitState mainState;
    static Map<String, Component> regs = new LinkedHashMap<String, Component>();
    static Map<String, CircuitState> regState = new LinkedHashMap<String, CircuitState>();

    public static void main(String[] args) throws Exception {
        File f = new File(args[0]);
        int cycles = Integer.parseInt(args[1]);

        Loader loader = new Loader(null);
        LogisimFile lf = loader.openLogisimFile(f);
        Project proj = new Project(lf);
        Circuit main = lf.getCircuit("main");
        CircuitState st = new CircuitState(proj, main);
        mainState = st;
        Propagator prop = st.getPropagator();
        prop.propagate();

        // PC = unico Register do circuito 'main'
        for (Component c : main.getNonWires()) {
            if (c.getFactory().getName().equals("Register")) pcReg = c;
        }
        // Registradores do Register Bank, ordenados por y (x0 .. x31)
        for (Component c : main.getNonWires()) {
            if (c.getFactory() instanceof SubcircuitFactory) {
                SubcircuitFactory sf = (SubcircuitFactory) c.getFactory();
                if (!sf.getSubcircuit().getName().equals("Register Bank")) continue;
                CircuitState sub = sf.getSubstate(st, c);
                List<Component> list = new ArrayList<Component>();
                for (Component rc : sf.getSubcircuit().getNonWires())
                    if (rc.getFactory().getName().equals("Register")) list.add(rc);
                Collections.sort(list, new Comparator<Component>() {
                    public int compare(Component a, Component b) {
                        return a.getLocation().getY() - b.getLocation().getY();
                    }
                });
                for (int i = 0; i < list.size(); i++) {
                    regs.put("x" + i, list.get(i));
                    regState.put("x" + i, sub);
                }
            }
        }

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < cycles; i++) {
            sb.append(String.format("ciclo %5d  PC=%s%n", i, val(st, pcReg)));
            prop.tick(); prop.propagate();   // clock high
            prop.tick(); prop.propagate();   // clock low
        }
        sb.append(String.format("ciclo %5d  PC=%s%n", cycles, val(st, pcReg)));
        sb.append("---- registradores ----\n");
        for (Map.Entry<String, Component> e : regs.entrySet()) {
            String v = val(regState.get(e.getKey()), e.getValue());
            if (!v.equals("00000000")) sb.append(String.format("%-4s = %s%n", e.getKey(), v));
        }
        System.out.print(sb);
        System.out.flush();
        System.exit(0);
    }

    static String val(CircuitState st, Component c) {
        Value v = st.getValue(c.getEnd(0).getLocation());
        if (v.isFullyDefined()) return String.format("%08x", v.toIntValue());
        return v.toString();
    }
}
