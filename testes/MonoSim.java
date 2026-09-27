import com.cburch.logisim.circuit.*;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.data.*;
import com.cburch.logisim.file.*;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.memory.Rom;
import java.io.File;
import java.lang.reflect.Method;
import java.util.*;

/**
 * Harness headless para o RISCV_Monociclo.circ.
 *
 *   java -cp /usr/share/logisim/logisim.jar:. MonoSim <arquivo.circ> <programa.mem> <ciclos>
 *
 * Carrega o programa na ROM de instrucoes (igual ao "Load Image" da GUI), da clock
 * ciclo a ciclo e imprime, a cada borda de subida (= uma instrucao):
 *   - o PC e a instrucao lida da ROM;
 *   - a escrita no banco de registradores que acontece nessa borda;
 *   - a escrita na memoria de dados que acontece nessa borda.
 * No fim imprime o banco de registradores e as palavras nao nulas da memoria de dados.
 */
public class MonoSim {

    public static void main(String[] args) throws Exception {
        File circ = new File(args[0]);
        File prog = new File(args[1]);
        int cycles = Integer.parseInt(args[2]);

        LogisimFile lf = new Loader(null).openLogisimFile(circ);
        Project proj = new Project(lf);
        Circuit main = lf.getMainCircuit();
        CircuitState st = new CircuitState(proj, main);
        Propagator prop = st.getPropagator();

        Component pc = null, regBank = null, rom = null, clock = null, dmem = null;
        for (Component c : main.getNonWires()) {
            String n = c.getFactory().getName();
            Object label = c.getAttributeSet().getAttributes().isEmpty() ? null : attr(c, "label");
            if (n.equals("Register") && "PC".equals(label)) pc = c;
            if (n.equals("RAM")) dmem = c;
            // ROM de instrucoes = a ROM de 32 bits (as outras sao de controle / ImmGen)
            if (n.equals("ROM") && "32".equals(String.valueOf(attr(c, "dataWidth")))) rom = c;
            if (n.equals("Clock")) clock = c;
            if (c.getFactory() instanceof SubcircuitFactory) {
                String sn = ((SubcircuitFactory) c.getFactory()).getSubcircuit().getName();
                if (sn.equals("Register Bank")) regBank = c;
            }
        }
        // Grava o programa direto no conteudo da ROM (limpa tudo antes). O Rom.loadImage
        // da API do Logisim 2.7.1 deixou a ROM zerada para programas curtos (< ~13 palavras).
        Object cont = rom.getAttributeSet().getValue(Rom.CONTENTS_ATTR);
        Method clr = cont.getClass().getMethod("clear"); clr.setAccessible(true); clr.invoke(cont);
        Method set = cont.getClass().getMethod("set", long.class, int.class); set.setAccessible(true);
        List<Integer> words = lerImagem(prog);
        for (int i = 0; i < words.size(); i++) set.invoke(cont, (long) i, words.get(i));
        prop.propagate();

        // Registradores do banco, por ordem de y (x0 .. x31)
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
                sb.append(String.format("C %d PC=%s INS=%s", cyc, hex(st, pc.getEnd(0)), hex(st, rom.getEnd(0))));
                if (st.getValue(regBank.getEnd(4).getLocation()) == Value.TRUE)
                    sb.append(String.format(" WB=%s:%s", dec(st, regBank.getEnd(2)), hex(st, regBank.getEnd(3))));
                if (st.getValue(dmem.getEnd(6).getLocation()) == Value.TRUE)
                    sb.append(String.format(" MEM=%s:%s", word2byte(st, dmem.getEnd(1)), hex(st, dmem.getEnd(7))));
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
        Object ms = st.getData(dmem);
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

    /** Le um arquivo "v2.0 raw" do Logisim (aceita repeticoes "N*valor"). */
    static List<Integer> lerImagem(File f) throws java.io.IOException {
        List<Integer> out = new ArrayList<Integer>();
        String txt = new String(java.nio.file.Files.readAllBytes(f.toPath()), "UTF-8");
        String[] tok = txt.trim().split("\\s+");
        int i = (tok.length > 1 && tok[0].equals("v2.0") && tok[1].equals("raw")) ? 2 : 0;
        for (; i < tok.length; i++) {
            String t = tok[i];
            int star = t.indexOf('*');
            if (star >= 0) {
                int n = Integer.parseInt(t.substring(0, star));
                int v = (int) Long.parseLong(t.substring(star + 1), 16);
                for (int k = 0; k < n; k++) out.add(v);
            } else {
                out.add((int) Long.parseLong(t, 16));
            }
        }
        return out;
    }

    static Object attr(Component c, String name) {
        for (com.cburch.logisim.data.Attribute<?> a : c.getAttributeSet().getAttributes())
            if (a.getName().equals(name)) return c.getAttributeSet().getValue(a);
        return null;
    }
    static String hex(CircuitState st, com.cburch.logisim.comp.EndData e) {
        Value v = st.getValue(e.getLocation());
        return v.isFullyDefined() ? String.format("%08x", v.toIntValue()) : v.toString().replace(' ', '_');
    }
    static String dec(CircuitState st, com.cburch.logisim.comp.EndData e) {
        Value v = st.getValue(e.getLocation());
        return v.isFullyDefined() ? Integer.toString(v.toIntValue()) : v.toString().replace(' ', '_');
    }
    static String word2byte(CircuitState st, com.cburch.logisim.comp.EndData e) {
        Value v = st.getValue(e.getLocation());
        return v.isFullyDefined() ? String.format("%08x", v.toIntValue() * 4) : v.toString().replace(' ', '_');
    }
}
