import com.cburch.logisim.circuit.*;
import com.cburch.logisim.comp.*;
import com.cburch.logisim.file.*;
import com.cburch.logisim.proj.Project;
import java.io.File;
import java.util.*;

public class Probe {
    public static void main(String[] a) throws Exception {
        LogisimFile lf = new Loader(null).openLogisimFile(new File(a[0]));
        new Project(lf);
        Circuit ci = lf.getCircuit(a[1]);
        Set<String> want = new HashSet<String>();
        for (int i = 2; i < a.length; i++) want.add(a[i]);
        StringBuilder sb = new StringBuilder();
        for (Component c : ci.getNonWires()) {
            String key = c.getLocation().getX() + "," + c.getLocation().getY();
            if (!want.contains(key)) continue;
            sb.append(c.getFactory().getName() + " @ (" + key + ")\n");
            for (int i = 0; i < c.getEnds().size(); i++) {
                EndData e = c.getEnd(i);
                sb.append(String.format("   porta %d  %-11s in=%-5s out=%-5s w=%s%n", i,
                    e.getLocation(), e.isInput(), e.isOutput(), e.getWidth()));
            }
        }
        System.out.print(sb);
        System.exit(0);
    }
}
